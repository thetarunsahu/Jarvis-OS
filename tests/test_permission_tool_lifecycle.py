from __future__ import annotations

from core.brain import Brain
from core.events import EventBus
from security.permissions import PermissionDecision, PermissionLevel
from tools.tool_registry import ToolRegistry, ToolSpec


class FakeProvider:
    def clear_history(self) -> None:
        pass


def test_confirm_tool_requests_permission_before_execution_finishes() -> None:
    events = EventBus()
    event_names: list[str] = []
    events.subscribe("*", lambda event: event_names.append(event.name))

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="confirm_test_tool",
            description="Test confirm lifecycle.",
            handler=lambda: {"message": "done"},
            permission=PermissionLevel.CONFIRM,
            permission_reason="Test approval.",
        )
    )

    brain = Brain(provider=FakeProvider(), tools=registry, events=events)
    brain.set_permission_approver(lambda request: PermissionDecision.ALLOW)

    result = brain.execute_tool("confirm_test_tool", {})

    assert result["ok"] is True
    assert "tool_started" not in event_names
    assert event_names.index("permission_required") < event_names.index(
        "permission_granted"
    )
    assert event_names.index("permission_granted") < event_names.index(
        "tool_finished"
    )


def test_denied_tool_never_looks_executed() -> None:
    events = EventBus()
    event_names: list[str] = []
    events.subscribe("*", lambda event: event_names.append(event.name))

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="denied_test_tool",
            description="Test denied lifecycle.",
            handler=lambda: {"message": "must not run"},
            permission=PermissionLevel.CONFIRM,
            permission_reason="Test approval.",
        )
    )

    brain = Brain(provider=FakeProvider(), tools=registry, events=events)
    brain.set_permission_approver(lambda request: PermissionDecision.DENY)

    result = brain.execute_tool("denied_test_tool", {})

    assert result["status"] == "permission_denied"
    assert "permission_required" in event_names
    assert "permission_denied" in event_names
    assert "permission_granted" not in event_names
    assert "tool_started" not in event_names
    assert event_names[-1] == "tool_finished"
