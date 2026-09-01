from core.intent_engine import IntentEngine
from models.model_router import ModelRouter
from tools.tool_registry import ToolRegistry


class Brain:
    """JARVIS intelligence entry point.

    Brain understands the request at a high level, then delegates model
    selection to ModelRouter. It never instantiates a specific AI vendor.
    """

    def __init__(self):
        self.intent_engine = IntentEngine()
        self.model_router = ModelRouter()
        self.tools = ToolRegistry()

    def respond(self, user_input, context=None):
        task = self.intent_engine.analyze(user_input)

        return self.model_router.generate(
            task=task,
            context=context,
            tools=self.tools.get_tool_definitions(),
            executor=self.tools.execute,
        )
