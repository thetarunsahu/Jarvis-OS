from __future__ import annotations

from core.events import EventBus
from providers.ollama_provider import OllamaProvider
from tools.tool_registry import ToolRegistry


class Brain:
    """Coordinates the model provider and the tool registry."""

    def __init__(
        self,
        provider: OllamaProvider | None = None,
        tools: ToolRegistry | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.provider = provider or OllamaProvider()
        self.tools = tools or ToolRegistry()
        self.events = events

    def respond(self, user_input: str) -> str:
        return self.provider.generate(
            user_input,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute,
            event_handler=self._handle_provider_event,
        )

    def clear_conversation(self) -> None:
        self.provider.clear_history()

    def _handle_provider_event(self, event_name: str, payload: dict) -> None:
        if self.events is not None:
            self.events.emit(event_name, **payload)
