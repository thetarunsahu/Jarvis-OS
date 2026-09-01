from __future__ import annotations

from core.task_runtime import (
    OperatingMode,
    StepStatus,
    TaskPlan,
    TaskRuntime,
    TaskStatus,
    TaskStep,
    VerificationStatus,
)


class FakeBrain:
    def __init__(self, results: list[dict]) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict, str]] = []

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        *,
        source: str = "deterministic_router",
    ) -> dict:
        self.calls.append((tool_name, arguments, source))
        if not self.results:
            raise AssertionError("No fake result remaining.")
        return self.results.pop(0)


def ok(data=None) -> dict:
    return {
        "ok": True,
        "tool": "fake",
        "status": "completed",
        "data": {} if data is None else data,
    }


def error(status: str = "execution_error", message: str = "boom") -> dict:
    return {
        "ok": False,
        "tool": "fake",
        "status": status,
        "error": message,
    }


def test_plan_runs_steps_in_order_and_does_not_fake_verification() -> None:
    brain = FakeBrain([ok(), ok()])
    runtime = TaskRuntime(brain)
    plan = TaskPlan(
        goal="prepare workspace",
        steps=(
            TaskStep(
                "one",
                "Open Chrome",
                "open_app",
                {"app_name": "chrome"},
            ),
            TaskStep(
                "two",
                "Search the web",
                "search_web",
                {"query": "jarvis"},
            ),
        ),
    )

    report = runtime.run(plan)

    assert report.status == TaskStatus.COMPLETED
    assert report.completed_steps == 2
    assert report.all_verified is False
    assert all(
        step.verification == VerificationStatus.UNVERIFIED
        for step in report.steps
    )
    assert brain.calls == [
        ("open_app", {"app_name": "chrome"}, "task_runtime"),
        ("search_web", {"query": "jarvis"}, "task_runtime"),
    ]


def test_explicit_verified_result_counts_as_verified() -> None:
    brain = FakeBrain([ok({"verified": True})])
    report = TaskRuntime(brain).run(
        TaskPlan(
            goal="verify a result",
            steps=(TaskStep("verify", "Verify it", "fake"),),
        )
    )

    assert report.status == TaskStatus.COMPLETED
    assert report.steps[0].verification == VerificationStatus.VERIFIED
    assert report.all_verified is True


def test_execution_error_retries_only_within_bound() -> None:
    brain = FakeBrain([error(), ok({"verified": True})])
    report = TaskRuntime(brain).run(
        TaskPlan(
            goal="retry once",
            steps=(
                TaskStep(
                    "retry",
                    "Retry a recoverable action",
                    "fake",
                    max_attempts=2,
                ),
            ),
        )
    )

    assert report.status == TaskStatus.COMPLETED
    assert report.steps[0].attempts == 2
    assert len(brain.calls) == 2


def test_permission_denial_blocks_remaining_plan() -> None:
    brain = FakeBrain([
        error("permission_denied", "denied"),
        ok(),
    ])
    report = TaskRuntime(brain).run(
        TaskPlan(
            goal="blocked task",
            mode=OperatingMode.AUTONOMOUS,
            steps=(
                TaskStep("first", "Needs approval", "fake"),
                TaskStep("second", "Must not execute", "fake_two"),
            ),
        )
    )

    assert report.status == TaskStatus.BLOCKED
    assert report.blocked_step_id == "first"
    assert report.steps[0].status == StepStatus.BLOCKED
    assert len(brain.calls) == 1


def test_unknown_tool_is_non_retryable_even_with_attempts_available() -> None:
    brain = FakeBrain([error("unknown_tool", "missing")])
    report = TaskRuntime(brain).run(
        TaskPlan(
            goal="invalid plan",
            steps=(
                TaskStep(
                    "unknown",
                    "Call missing tool",
                    "missing_tool",
                    max_attempts=3,
                ),
            ),
        )
    )

    assert report.status == TaskStatus.BLOCKED
    assert report.steps[0].status == StepStatus.BLOCKED
    assert report.steps[0].attempts == 1
    assert len(brain.calls) == 1


def test_plan_rejects_duplicate_step_ids() -> None:
    try:
        TaskPlan(
            goal="invalid duplicate IDs",
            steps=(
                TaskStep("same", "One", "fake"),
                TaskStep("same", "Two", "fake"),
            ),
        )
    except ValueError as exc:
        assert "unique" in str(exc).lower()
    else:
        raise AssertionError("Expected duplicate step IDs to be rejected.")
