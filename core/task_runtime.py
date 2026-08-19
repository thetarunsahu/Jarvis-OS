from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from core.brain import Brain
from core.events import EventBus


class OperatingMode(str, Enum):
    """High-level autonomy policy for a task plan."""

    LEARN = "learn"
    ASSIST = "assist"
    AUTONOMOUS = "autonomous"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    FAILED = "failed"


@dataclass(frozen=True)
class TaskStep:
    """One concrete tool action inside a task plan."""

    step_id: str
    description: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = 1
    continue_on_failure: bool = False

    def __post_init__(self) -> None:
        if not self.step_id.strip():
            raise ValueError("TaskStep.step_id cannot be empty.")
        if not self.tool_name.strip():
            raise ValueError("TaskStep.tool_name cannot be empty.")
        if not 1 <= self.max_attempts <= 3:
            raise ValueError("TaskStep.max_attempts must be between 1 and 3.")


@dataclass(frozen=True)
class TaskPlan:
    """A bounded sequence of explicit tool actions for one user goal."""

    goal: str
    steps: tuple[TaskStep, ...]
    mode: OperatingMode = OperatingMode.ASSIST

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("TaskPlan.goal cannot be empty.")
        if not self.steps:
            raise ValueError("TaskPlan requires at least one step.")
        if len(self.steps) > 32:
            raise ValueError("TaskPlan cannot contain more than 32 steps.")

        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("TaskPlan step IDs must be unique.")


@dataclass(frozen=True)
class StepResult:
    step_id: str
    description: str
    tool_name: str
    status: StepStatus
    verification: VerificationStatus
    attempts: int
    tool_result: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class TaskReport:
    goal: str
    mode: OperatingMode
    status: TaskStatus
    steps: tuple[StepResult, ...]
    blocked_step_id: str | None = None

    @property
    def all_verified(self) -> bool:
        return bool(self.steps) and all(
            step.status == StepStatus.COMPLETED
            and step.verification == VerificationStatus.VERIFIED
            for step in self.steps
        )

    @property
    def completed_steps(self) -> int:
        return sum(step.status == StepStatus.COMPLETED for step in self.steps)

    def summary(self) -> str:
        if self.status == TaskStatus.COMPLETED:
            verification = "verified" if self.all_verified else "not fully verified"
            return (
                f"Task completed: {self.completed_steps}/{len(self.steps)} steps; "
                f"result is {verification}."
            )

        if self.status == TaskStatus.BLOCKED:
            return (
                f"Task blocked at step {self.blocked_step_id or 'unknown'} after "
                f"{self.completed_steps}/{len(self.steps)} completed steps."
            )

        return (
            f"Task failed after {self.completed_steps}/{len(self.steps)} completed steps."
        )


class TaskRuntime:
    """Executes explicit task plans with bounded retries and truthful verification.

    This runtime deliberately does not invent plans. A planner may create a
    TaskPlan later, but execution always happens through the existing Brain and
    ToolRegistry so permissions remain authoritative.
    """

    _NON_RETRYABLE_STATUSES = {
        "permission_denied",
        "unknown_tool",
    }

    def __init__(self, brain: Brain, events: EventBus | None = None) -> None:
        self.brain = brain
        self.events = events

    def run(self, plan: TaskPlan) -> TaskReport:
        self._emit(
            "task_started",
            goal=plan.goal,
            mode=plan.mode.value,
            total_steps=len(plan.steps),
        )

        step_results: list[StepResult] = []
        blocked_step_id: str | None = None
        task_status = TaskStatus.RUNNING

        for index, step in enumerate(plan.steps, start=1):
            self._emit(
                "task_step_started",
                goal=plan.goal,
                step_id=step.step_id,
                description=step.description,
                tool_name=step.tool_name,
                index=index,
                total_steps=len(plan.steps),
            )

            step_result = self._run_step(step)
            step_results.append(step_result)

            self._emit(
                "task_step_finished",
                goal=plan.goal,
                step_id=step.step_id,
                status=step_result.status.value,
                verification=step_result.verification.value,
                attempts=step_result.attempts,
                error=step_result.error,
            )

            if step_result.status == StepStatus.COMPLETED:
                continue

            if step.continue_on_failure:
                continue

            blocked_step_id = step.step_id
            task_status = (
                TaskStatus.BLOCKED
                if step_result.status == StepStatus.BLOCKED
                else TaskStatus.FAILED
            )
            break
        else:
            task_status = TaskStatus.COMPLETED

        report = TaskReport(
            goal=plan.goal,
            mode=plan.mode,
            status=task_status,
            steps=tuple(step_results),
            blocked_step_id=blocked_step_id,
        )

        self._emit(
            "task_finished",
            goal=plan.goal,
            mode=plan.mode.value,
            status=report.status.value,
            completed_steps=report.completed_steps,
            total_steps=len(plan.steps),
            all_verified=report.all_verified,
            blocked_step_id=report.blocked_step_id,
        )
        return report

    def _run_step(self, step: TaskStep) -> StepResult:
        last_result: dict[str, Any] = {}
        last_error: str | None = None

        for attempt in range(1, step.max_attempts + 1):
            result = self.brain.execute_tool(
                step.tool_name,
                dict(step.arguments),
                source="task_runtime",
            )
            last_result = result

            if result.get("ok"):
                return StepResult(
                    step_id=step.step_id,
                    description=step.description,
                    tool_name=step.tool_name,
                    status=StepStatus.COMPLETED,
                    verification=self._verification_status(result),
                    attempts=attempt,
                    tool_result=result,
                )

            status = str(result.get("status") or "execution_error")
            last_error = str(result.get("error") or "Unknown tool error.")

            if status in self._NON_RETRYABLE_STATUSES:
                return StepResult(
                    step_id=step.step_id,
                    description=step.description,
                    tool_name=step.tool_name,
                    status=StepStatus.BLOCKED,
                    verification=VerificationStatus.FAILED,
                    attempts=attempt,
                    tool_result=result,
                    error=last_error,
                )

            if attempt < step.max_attempts:
                self._emit(
                    "task_step_retry",
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    error=last_error,
                )
                continue

            return StepResult(
                step_id=step.step_id,
                description=step.description,
                tool_name=step.tool_name,
                status=StepStatus.FAILED,
                verification=VerificationStatus.FAILED,
                attempts=attempt,
                tool_result=result,
                error=last_error,
            )

        return StepResult(
            step_id=step.step_id,
            description=step.description,
            tool_name=step.tool_name,
            status=StepStatus.FAILED,
            verification=VerificationStatus.FAILED,
            attempts=step.max_attempts,
            tool_result=last_result,
            error=last_error or "Task step failed.",
        )

    @staticmethod
    def _verification_status(result: dict[str, Any]) -> VerificationStatus:
        if not result.get("ok"):
            return VerificationStatus.FAILED

        data = result.get("data")
        if isinstance(data, dict) and "verified" in data:
            return (
                VerificationStatus.VERIFIED
                if data.get("verified") is True
                else VerificationStatus.UNVERIFIED
            )

        # Execution success and outcome verification are intentionally distinct.
        # A future verifier may upgrade this to VERIFIED using an independent
        # observation (file existence, process state, browser state, test output).
        return VerificationStatus.UNVERIFIED

    def _emit(self, event_name: str, **payload: Any) -> None:
        if self.events is not None:
            self.events.emit(event_name, **payload)
