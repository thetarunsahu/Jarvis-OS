from agents.model_agent import ModelAgent
from research.openai_web_research import OpenAIWebResearchRuntime


class ResearchAgent(ModelAgent):
    """Research specialist with an optional hosted web-search runtime."""

    def __init__(
        self,
        model_router,
        tool_registry,
        research_runtime=None,
    ):
        super().__init__(
            name="research",
            intents={"research"},
            instructions="""
You are the JARVIS Research Agent. Separate evidence from inference, prefer
primary sources when tools are available, track uncertainty, and never claim
fresh internet research unless a browsing or research runtime actually ran.
If fresh web access is unavailable, say that clearly and provide only the
analysis that can be supported from available context.
""",
            model_router=model_router,
            tool_registry=tool_registry,
        )
        self.research_runtime = research_runtime or OpenAIWebResearchRuntime()

    def execute(self, task, context=None):
        if self.research_runtime.is_available:
            task.metadata["research_runtime"] = "openai_web_search"
            return self.research_runtime.research(
                task.raw_input,
                context=context,
            )

        task.metadata["research_runtime"] = "model_fallback"
        return super().execute(task, context=context)
