from core.events import EventBus
from core.orchestrator import JarvisOrchestrator
from core.state import JarvisState


class FakeRouter:
    def __init__(self, response="ok", error=None, events=None):
        self.response = response
        self.error = error
        self.events = events

    def route(self, user_input):
        if self.error:
            raise self.error

        if self.events is not None:
            self.events.emit("tool_started", tool_name="fake_tool", arguments={})
            self.events.emit("tool_finished", tool_name="fake_tool", result="done")

        return self.response


def test_process_emits_state_and_response_events():
    events = EventBus()
    seen = []
    events.subscribe("*", lambda event: seen.append(event))

    orchestrator = JarvisOrchestrator(
        router=FakeRouter("hello"),
        events=events,
    )

    response = orchestrator.process("hi")

    assert response == "hello"
    assert orchestrator.state == JarvisState.READY
    assert [event.name for event in seen] == [
        "request_started",
        "state_changed",
        "response_ready",
        "state_changed",
    ]
    assert seen[1].payload["current"] == "THINKING"
    assert seen[-1].payload["current"] == "READY"


def test_tool_events_drive_execution_and_verification_states():
    events = EventBus()
    seen = []
    events.subscribe("*", lambda event: seen.append(event))

    orchestrator = JarvisOrchestrator(
        router=FakeRouter("done", events=events),
        events=events,
    )

    response = orchestrator.process("use a tool")

    assert response == "done"
    transitions = [
        event.payload["current"]
        for event in seen
        if event.name == "state_changed"
    ]
    assert transitions == ["THINKING", "EXECUTING", "VERIFYING", "READY"]
    assert any(event.name == "tool_started" for event in seen)
    assert any(event.name == "tool_finished" for event in seen)


def test_process_handles_router_error_without_crashing():
    events = EventBus()
    seen = []
    events.subscribe("*", lambda event: seen.append(event))

    orchestrator = JarvisOrchestrator(
        router=FakeRouter(error=RuntimeError("boom")),
        events=events,
    )

    response = orchestrator.process("anything")

    assert response == "I hit an internal error while processing that request."
    assert orchestrator.state == JarvisState.ERROR
    assert any(event.name == "error" for event in seen)


def test_blank_input_does_not_invoke_router():
    orchestrator = JarvisOrchestrator(router=FakeRouter("unused"))

    assert orchestrator.process("   ") == ""
    assert orchestrator.state == JarvisState.READY
