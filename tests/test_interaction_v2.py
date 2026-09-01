from __future__ import annotations

from core.router import CommandRouter
from security.permissions import (
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    PermissionRequest,
)


class FakeMemory:
    pass


class FakeBrain:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.fallback_calls: list[str] = []

    def execute_tool(self, tool_name: str, arguments: dict | None = None):
        payload = arguments or {}
        self.calls.append((tool_name, payload))
        return {
            "ok": True,
            "tool": tool_name,
            "status": "completed",
            "data": {"message": f"{tool_name} completed"},
        }

    def respond(self, text: str) -> str:
        self.fallback_calls.append(text)
        return "fallback"

    def clear_conversation(self) -> None:
        pass

    def set_permission_approver(self, approver) -> None:
        pass


def test_confirm_permission_can_be_granted_for_session() -> None:
    approvals = 0

    def approver(request):
        nonlocal approvals
        approvals += 1
        return PermissionDecision.ALLOW_SESSION

    manager = PermissionManager(approver=approver)
    request = PermissionRequest(
        tool_name="set_volume",
        arguments={"percent": 30},
        level=PermissionLevel.CONFIRM,
        reason="change audio state",
    )

    assert manager.authorize(request) == PermissionDecision.ALLOW
    assert manager.authorize(request) == PermissionDecision.ALLOW
    assert approvals == 1
    assert manager.is_session_granted("set_volume") is True


def test_destructive_permission_is_never_cached_for_session() -> None:
    approvals = 0

    def approver(request):
        nonlocal approvals
        approvals += 1
        return PermissionDecision.ALLOW_SESSION

    manager = PermissionManager(approver=approver)
    request = PermissionRequest(
        tool_name="shutdown_computer",
        arguments={"delay_seconds": 30},
        level=PermissionLevel.DESTRUCTIVE,
        reason="power action",
    )

    assert manager.authorize(request) == PermissionDecision.ALLOW
    assert manager.authorize(request) == PermissionDecision.ALLOW
    assert approvals == 2
    assert manager.is_session_granted("shutdown_computer") is False


def test_open_chrome_uses_fast_lane_without_model_fallback() -> None:
    brain = FakeBrain()
    router = CommandRouter(memory=FakeMemory(), brain=brain)

    response = router.route("open chrome")

    assert response == "open_app completed"
    assert brain.calls == [("open_app", {"app_name": "chrome"})]
    assert brain.fallback_calls == []


def test_running_apps_uses_fast_lane_without_model_fallback() -> None:
    brain = FakeBrain()
    router = CommandRouter(memory=FakeMemory(), brain=brain)

    response = router.route("which applications are running")

    assert response == "list_running_apps completed"
    assert brain.calls == [("list_running_apps", {})]
    assert brain.fallback_calls == []
