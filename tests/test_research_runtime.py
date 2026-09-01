import unittest
from types import SimpleNamespace

from agents.research_agent import ResearchAgent
from core.task import Task
from research.openai_web_research import OpenAIWebResearchRuntime


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        annotation = SimpleNamespace(
            type="url_citation",
            url="https://example.com/source",
            title="Primary Source",
        )
        content = SimpleNamespace(
            type="output_text",
            annotations=[annotation],
        )
        message = SimpleNamespace(type="message", content=[content])
        return SimpleNamespace(
            output=[message],
            output_text="Research synthesis.",
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


class FakeRouter:
    def generate(self, *args, **kwargs):
        return "fallback"


class FakeTools:
    def get_tool_definitions(self):
        return []

    def execute(self, *args, **kwargs):
        return None


class FakeRuntime:
    is_available = True

    def research(self, query, context=None):
        return f"fresh:{query}|{context or ''}"


class ResearchRuntimeTests(unittest.TestCase):
    def test_web_runtime_requests_hosted_search_and_renders_sources(self):
        client = FakeClient()
        runtime = OpenAIWebResearchRuntime(client=client)

        result = runtime.research("latest agent frameworks")

        self.assertIn("Research synthesis.", result)
        self.assertIn("Primary Source", result)
        self.assertIn("https://example.com/source", result)
        request = client.responses.calls[0]
        self.assertEqual(request["tools"], [{"type": "web_search_preview"}])
        self.assertIn("web_search_call.action.sources", request["include"])

    def test_research_agent_uses_specialist_runtime_when_available(self):
        agent = ResearchAgent(
            model_router=FakeRouter(),
            tool_registry=FakeTools(),
            research_runtime=FakeRuntime(),
        )
        task = Task(
            raw_input="deep research agent architectures",
            intent="research",
            background=True,
        )

        result = agent.execute(task, context="project=Jarvis")

        self.assertIn("fresh:deep research agent architectures", result)
        self.assertEqual(task.metadata["research_runtime"], "openai_web_search")


if __name__ == "__main__":
    unittest.main()
