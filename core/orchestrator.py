from __future__ import annotations

from core.events import EventBus
from core.router import CommandRouter
from core.state import JarvisState


class JarvisOrchestrator:
    """Central entry point for JARVIS requests.

    UI, CLI, and voice layers should call this class instead of talking to
    providers/tools directly. It owns runtime state and emits observable events.
    """

    def __init__(
        self,
        router: CommandRouter | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.router = router or CommandRouter()
        self.events = events or EventBus()
        self.state = JarvisState.READY

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
