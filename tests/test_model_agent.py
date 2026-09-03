import unittest

from agents.model_agent import ModelAgent
from core.task import Task


class FakeModelRouter:
    def __init__(self):
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return "ok"


class FakeToolRegistry:
    def __init__(self):
        self.definition_calls = 0
        self.execute_calls = []

    def get_tool_definitions(self):
        self.definition_calls += 1
        return [{"type": "function", "function": {"name": "demo"}}]

    def execute(self, tool_name, arguments=None, task_id=None):
        self.execute_calls.append((tool_name, arguments, task_id))
        return "tool-result"


class ModelAgentTests(unittest.TestCase):
    def setUp(self):
        self.router = FakeModelRouter()
        self.tools = FakeToolRegistry()
        self.agent = ModelAgent(
            name="general",
            intents={"conversation", "system"},
            instructions="Answer naturally.",
            model_router=self.router,
            tool_registry=self.tools,
        )

    def test_conversation_does_not_expose_tool_catalog(self):
        task = Task(raw_input="tell me something interesting", requires_tools=False)

        result = self.agent.execute(task)

        self.assertEqual(result, "ok")
        self.assertEqual(self.tools.definition_calls, 0)
        self.assertIsNone(self.router.calls[-1]["tools"])
        self.assertIsNone(self.router.calls[-1]["executor"])

    def test_tool_required_task_exposes_tools_and_executor(self):
        task = Task(
            raw_input="show cpu usage",
            intent="system",
            requires_tools=True,
        )

        result = self.agent.execute(task)

        self.assertEqual(result, "ok")
        self.assertEqual(self.tools.definition_calls, 1)
        self.assertEqual(self.router.calls[-1]["tools"][0]["function"]["name"], "demo")
        self.assertTrue(callable(self.router.calls[-1]["executor"]))


if __name__ == "__main__":
    unittest.main()
