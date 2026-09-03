import unittest

from agents.agent_registry import AgentRegistry
from agents.agent_router import AgentRouter
from core.task import Task


class FakeModelRouter:
    def generate(self, task, context=None, tools=None, executor=None):
        return "ok"


class FakeTools:
    def get_tool_definitions(self):
        return []

    def execute(self, tool_name, arguments=None, approved=False):
        return None


class AgentRouterTests(unittest.TestCase):
    def setUp(self):
        registry = AgentRegistry(FakeModelRouter(), FakeTools())
        self.router = AgentRouter(registry)

    def test_coding_intent_routes_to_coding_agent(self):
        task = Task(raw_input="fix this bug", intent="coding")
        agent = self.router.route(task)
        self.assertEqual(agent.name, "coding")

    def test_unknown_intent_falls_back_to_general(self):
        task = Task(raw_input="something new", intent="unknown")
        agent = self.router.route(task)
        self.assertEqual(agent.name, "general")


if __name__ == "__main__":
    unittest.main()
