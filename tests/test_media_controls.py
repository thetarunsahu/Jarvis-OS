from __future__ import annotations

from core.language import normalize_for_routing
from core.router import CommandRouter
from tools.media_extension import register_media_tools
from tools.tool_registry import ToolRegistry


class _Memory:
    def get_all(self):
        return {}

    def remember(self, key: str, value: str):
        return {"key": key, "value": value}

    def recall(self, key: str):
        return None

    def forget(self, key: str):
        return None


class _Brain:
    def __init__(self) -> None:
        self.tool_calls: list[tuple[str, dict]] = []

    def execute_tool(self, name: str, arguments: dict):
        self.tool_calls.append((name, arguments))
        return {
            "ok": True,
            "status": "success",
            "data": {"message": "media command sent"},
        }

    def respond(self, text: str) -> str:
        return "model response"

    def clear_conversation(self) -> None:
        return None

    def set_permission_approver(self, approver) -> None:
        return None


def test_hinglish_next_song_normalizes_to_media_command():
    assert normalize_for_routing("agla gana kar do") == "next track"


def test_router_sends_media_next_without_model_round_trip():
    brain = _Brain()
    router = CommandRouter(memory=_Memory(), brain=brain)

    result = router.route("agla gana kar do")

    assert result == "media command sent"
    assert brain.tool_calls == [("media_next", {})]


def test_media_capability_pack_registers_confirm_tools():
    registry = ToolRegistry()
    register_media_tools(registry)

    names = set(registry.get_tool_names())
    assert {
        "media_play_pause",
        "media_next",
        "media_previous",
        "media_stop",
    }.issubset(names)

    result = registry.execute("media_next", {})
    assert result["ok"] is False
    assert result["status"] == "permission_denied"
