import unittest

from core.task import Task
from models.model_router import ModelRouter


class FakeProvider:
    def __init__(self, name, local, supports_tools, result=None, available=True):
        self.name = name
        self.local = local
        self.supports_tools = supports_tools
        self.result = result or name
        self.is_available = available

    def generate(self, user_input, context=None, tools=None, executor=None):
        return self.result


class FakeRegistry:
    def __init__(self):
        self.providers = {
            "local": FakeProvider("local", True, True, result="local-result"),
            "cloud": FakeProvider("cloud", False, False, result="cloud-result"),
        }

    def names(self):
        return list(self.providers.keys())

    def get(self, name):
        return self.providers[name]


class ModelRouterTests(unittest.TestCase):
    def test_auto_routing_prefers_local_provider(self):
        router = ModelRouter(registry=FakeRegistry())
        router.default_provider = "auto"
        task = Task(raw_input="hello")

        result = router.generate(task)

        self.assertEqual(result, "local-result")

    def test_explicit_cloud_provider_is_respected_without_tools(self):
        router = ModelRouter(registry=FakeRegistry())
        router.default_provider = "cloud"
        task = Task(raw_input="hello")

        result = router.generate(task)

        self.assertEqual(result, "cloud-result")


if __name__ == "__main__":
    unittest.main()
