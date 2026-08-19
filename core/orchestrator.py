from __future__ import annotations

from core.events import EventBus, JarvisEvent
from core.router import CommandRouter
from core.state import JarvisState
from core.task_runtime import TaskPlan, TaskReport, TaskRuntime
from security.permissions import Approver


class JarvisOrchestrator:
    """Central entry point for JARVIS requests.

    UI, CLI, and voice layers should call this class instead of talking to
    providers or tools directly. It owns runtime state and emits observable
    events that the interface can subscribe to.
    """

    def __init__(
        self,
        router: CommandRouter | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.events = events or EventBus()
        self.router = router or CommandRouter(events=self.events)
        self.task_runtime = TaskRuntime(self.router.brain, events=self.events)
        self.state = JarvisState.READY

        self.events.subscribe("tool_started", self._on_tool_started)
        self.events.subscribe("tool_finished", self._on_tool_finished)
        self.events.subscribe("permission_required", self._on_permission_required)
        self.events.subscribe("permission_granted", self._on_permission_granted)
        self.events.subscribe("permission_denied", self._on_permission_denied)
        self.events.subscribe("agent_limit_reached", self._on_agent_limit_reached)

    def set_state(self, state: JarvisState) -> None:
        if state == self.state:
            return

        previous = self.state
        self.state = state
        self.events.emit(
            "state_changed",
            previous=previous.value,
            current=state.value,
        )

    def set_permission_approver(self, approver: Approver | None) -> None:
        """Attach the UI/CLI callback that approves higher-risk tools."""
        self.router.set_permission_approver(approver)

    def process(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        self.events.emit("request_started", text=text)
        self.set_state(JarvisState.THINKING)

        try:
            response = self.router.route(text)

            if response is None:
                response = (
                    "I don't understand that command yet. "
                    "Type 'help' to see what I can currently do."
                )

            response = str(response)
            self.events.emit("response_ready", text=response)
            self.set_state(JarvisState.READY)
            return response

        except Exception as error:
            self.set_state(JarvisState.ERROR)
            self.events.emit(
                "error",
                error_type=type(error).__name__,
                message=str(error),
            )
            return "I hit an internal error while processing that request."

    def run_plan(self, plan: TaskPlan) -> TaskReport:
        """Execute an already-validated task plan through the shared runtime."""

        self.events.emit(
            "request_started",
            text=plan.goal,
            source="task_plan",
        )
        self.set_state(JarvisState.THINKING)

        try:
            report = self.task_runtime.run(plan)
            self.events.emit(
                "task_report_ready",
                goal=report.goal,
                status=report.status.value,
                summary=report.summary(),
                all_verified=report.all_verified,
            )
            self.set_state(JarvisState.READY)
            return report
        except Exception as error:
            self.set_state(JarvisState.ERROR)
            self.events.emit(
                "error",
                error_type=type(error).__name__,
                message=str(error),
                source="task_plan",
            )
            raise

    def _on_tool_started(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.EXECUTING)

    def _on_tool_finished(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.VERIFYING)

    def _on_permission_required(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.AWAITING_PERMISSION)

    def _on_permission_granted(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.EXECUTING)

    def _on_permission_denied(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.VERIFYING)

    def _on_agent_limit_reached(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.ERROR)
