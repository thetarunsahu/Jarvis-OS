import unittest
from types import SimpleNamespace

from providers.openai_provider import OpenAIProvider


class FakeResponsesAPI:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if len(self.calls) == 1 and kwargs.get("tools"):
            return SimpleNamespace(
                id="resp_1",
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="current_time",
                        arguments="{}",
                        call_id="call_1",
                    )
                ],
                output_text="",
            )

        return SimpleNamespace(
            id=f"resp_{len(self.calls)}",
            output=[],
            output_text="The time is 10:30 PM.",
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponsesAPI()


class OpenAIProviderTests(unittest.TestCase):
    def test_converts_internal_tool_schema_for_responses_api(self):
        provider = OpenAIProvider(client=FakeClient())

        converted = provider._convert_tools(
            [
                {
                    "type": "function",
                    "function": {
                        "name": "current_time",
                        "description": "Get current time.",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                }
            ]
        )

        self.assertEqual(converted[0]["type"], "function")
        self.assertEqual(converted[0]["name"], "current_time")
        self.assertNotIn("function", converted[0])

    def test_executes_function_call_and_returns_final_text(self):
        client = FakeClient()
        provider = OpenAIProvider(client=client)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "current_time",
                    "description": "Get current time.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            }
        ]
        executed = []

        def executor(name, arguments):
            executed.append((name, arguments))
            return {"time": "10:30 PM"}

        result = provider.generate(
            "what time is it?",
            tools=tools,
            executor=executor,
        )

        self.assertEqual(result, "The time is 10:30 PM.")
        self.assertEqual(executed, [("current_time", {})])
        self.assertEqual(len(client.responses.calls), 2)

        first = client.responses.calls[0]
        self.assertEqual(first["tools"][0]["name"], "current_time")
        self.assertEqual(first["tool_choice"], "auto")

        second = client.responses.calls[1]
        self.assertEqual(second["previous_response_id"], "resp_1")
        self.assertEqual(second["input"][0]["type"], "function_call_output")
        self.assertEqual(second["input"][0]["call_id"], "call_1")
        self.assertIn("10:30 PM", second["input"][0]["output"])

    def test_normal_response_does_not_require_tools(self):
        client = FakeClient()
        provider = OpenAIProvider(client=client)

        result = provider.generate("hello")

        self.assertEqual(result, "The time is 10:30 PM.")
        self.assertNotIn("tools", client.responses.calls[0])


if __name__ == "__main__":
    unittest.main()
