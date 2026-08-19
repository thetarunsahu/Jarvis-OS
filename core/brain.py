from __future__ import annotations

from typing import Any

from core.events import EventBus
from providers.ollama_provider import OllamaProvider
from security.permissions import Approver
from tools.tool_registry import ToolRegistry
from tools.media_extension import register_media_tools


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

        register_media_tools(self.tools)

    def respond(self, user_input: str) -> str:
        return self.provider.generate(
            user_input,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute,
            event_handler=self._handle_event,
        )

    def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a known tool outside the model loop while preserving events.

        This is used for high-confidence deterministic commands such as
        "set volume to 30%". It avoids depending on the language model to decide
        whether a clearly matching local capability exists, while permissions
        are still enforced by ToolRegistry.
        """

        payload = arguments or {}
        self._handle_event(
            "tool_started",
            {
                "tool_name": tool_name,
                "arguments": payload,
                "source": "deterministic_router",
            },
        )
        result = self.tools.execute(tool_name, payload)
        self._handle_event(
            "tool_finished",
            {
                "tool_name": tool_name,
                "result": result,
                "source": "deterministic_router",
            },
        )
        return result

    def clear_conversation(self) -> None:
        self.provider.clear_history()

    def set_permission_approver(self, approver: Approver | None) -> None:
        self.tools.set_permission_approver(approver)

    def _handle_event(self, event_name: str, payload: dict) -> None:
        if self.events is not None:
            self.events.emit(event_name, **payload)
