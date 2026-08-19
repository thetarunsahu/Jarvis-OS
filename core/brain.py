from providers.ollama_provider import OllamaProvider
from tools.tool_registry import ToolRegistry


class Brain:

    def __init__(self):

        self.provider = OllamaProvider()
        self.tools = ToolRegistry()

    def respond(self, user_input):

        return self.provider.generate(
            user_input,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute
        )