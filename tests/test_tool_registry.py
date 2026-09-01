from security.permissions import PermissionLevel
from tools.tool_registry import ToolRegistry, ToolSpec


def test_safe_tool_executes_without_approval():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="echo_safe",
            description="Return a value without side effects.",
            handler=lambda value="ok": value,
            parameters={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "additionalProperties": False,
            },
        )
    )

    result = registry.execute("echo_safe", {"value": "hello"})

    assert result["ok"] is True
    assert result["data"] == "hello"


def test_confirm_tool_is_denied_without_approver():
    called = []
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="needs_confirmation",
            description="A test action that requires approval.",
            handler=lambda: called.append(True),
            permission=PermissionLevel.CONFIRM,
            permission_reason="Test approval gate.",
        )
    )

    result = registry.execute("needs_confirmation")

    assert result["ok"] is False
    assert result["status"] == "permission_denied"
    assert called == []


def test_confirm_tool_executes_after_explicit_approval():
    events = []
    registry = ToolRegistry(
        event_handler=lambda name, payload: events.append((name, payload))
    )
    registry.register(
        ToolSpec(
            name="approved_action",
            description="A test action that requires approval.",
            handler=lambda: "done",
            permission=PermissionLevel.CONFIRM,
            permission_reason="Test approval gate.",
        )
    )
    registry.set_permission_approver(lambda request: True)

    result = registry.execute("approved_action")

    assert result["ok"] is True
    assert result["data"] == "done"
    assert [name for name, _ in events] == [
        "permission_required",
        "permission_granted",
    ]


def test_unknown_tool_returns_structured_error():
    registry = ToolRegistry()

    result = registry.execute("does_not_exist")

    assert result == {
        "ok": False,
        "tool": "does_not_exist",
        "status": "unknown_tool",
        "error": "Unknown tool: does_not_exist",
    }
