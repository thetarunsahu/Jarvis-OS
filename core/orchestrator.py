from __future__ import annotations

from core.events import EventBus, JarvisEvent
from core.router import CommandRouter
from core.state import JarvisState


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
        self.state = JarvisState.READY

        self.events.subscribe("tool_started", self._on_tool_started)
        self.events.subscribe("tool_finished", self._on_tool_finished)
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

    def _on_tool_started(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.EXECUTING)

    def _on_tool_finished(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.VERIFYING)

    def _on_agent_limit_reached(self, event: JarvisEvent) -> None:
        self.set_state(JarvisState.ERROR)
