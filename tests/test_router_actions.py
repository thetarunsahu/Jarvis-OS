from __future__ import annotations

from core.router import CommandRouter


class FakeBrain:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.respond_calls: list[str] = []
        self.result = {
            "ok": True,
            "status": "completed",
            "data": {"message": "done"},
        }

    def execute_tool(self, tool_name: str, arguments: dict):
        self.calls.append((tool_name, arguments))
        return self.result

    def respond(self, user_input: str) -> str:
        self.respond_calls.append(user_input)
        return "model response"

    def clear_conversation(self) -> None:
        pass

    def set_permission_approver(self, approver) -> None:
        pass


def test_set_volume_routes_directly_without_model() -> None:
    brain = FakeBrain()
    router = CommandRouter(brain=brain)

    response = router.route("set volume to 30%")

    assert response == "done"
    assert brain.calls == [("set_volume", {"percent": 30})]
    assert brain.respond_calls == []


def test_set_volume_accepts_percent_word() -> None:
    brain = FakeBrain()
    router = CommandRouter(brain=brain)

    router.route("set the system volume to 45 percent")

    assert brain.calls == [("set_volume", {"percent": 45})]


def test_youtube_search_routes_directly() -> None:
    brain = FakeBrain()
    router = CommandRouter(brain=brain)

    router.route("search youtube for hans zimmer")

    assert brain.calls == [("search_youtube", {"query": "hans zimmer"})]


def test_shutdown_delay_is_parsed_in_seconds() -> None:
    brain = FakeBrain()
    router = CommandRouter(brain=brain)

    router.route("shutdown the computer in 1 minute")

    assert brain.calls == [("shutdown_computer", {"delay_seconds": 60})]


def test_normal_conversation_still_falls_back_to_model() -> None:
    brain = FakeBrain()
    router = CommandRouter(brain=brain)

    response = router.route("explain recursion simply")

    assert response == "model response"
    assert brain.calls == []
    assert brain.respond_calls == ["explain recursion simply"]


def test_permission_denial_is_reported_cleanly() -> None:
    brain = FakeBrain()
    brain.result = {
        "ok": False,
        "status": "permission_denied",
        "error": "User approval was not granted.",
    }
    router = CommandRouter(brain=brain)

    response = router.route("set volume to 30%")

    assert response == "Action cancelled because permission was not granted."
