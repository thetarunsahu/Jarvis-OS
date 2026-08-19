from __future__ import annotations

from core.events import EventBus
from providers.ollama_provider import OllamaProvider
from security.permissions import Approver
from tools.tool_registry import ToolRegistry


class Brain:
    """Coordinates the model provider, tool registry, and core events."""

    def __init__(
        self,
        provider: OllamaProvider | None = None,
        tools: ToolRegistry | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.events = events
        self.provider = provider or OllamaProvider()

        if tools is None:
            self.tools = ToolRegistry(event_handler=self._handle_event)
        else:
            self.tools = tools
            self.tools.set_event_handler(self._handle_event)

    def respond(self, user_input: str) -> str:
        return self.provider.generate(
            user_input,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute,
            event_handler=self._handle_event,
        )

    def clear_conversation(self) -> None:
        self.provider.clear_history()

    def set_permission_approver(self, approver: Approver | None) -> None:
        self.tools.set_permission_approver(approver)

    def _handle_event(self, event_name: str, payload: dict) -> None:
        if self.events is not None:
            self.events.emit(event_name, **payload)
