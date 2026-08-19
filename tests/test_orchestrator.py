from core.events import EventBus
from core.orchestrator import JarvisOrchestrator
from core.state import JarvisState


class FakeRouter:
    def __init__(self, response="ok", error=None):
        self.response = response
        self.error = error

    def route(self, user_input):
        if self.error:
            raise self.error
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
