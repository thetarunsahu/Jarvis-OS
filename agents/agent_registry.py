from agents.model_agent import ModelAgent


class AgentRegistry:
    """Registry of specialist JARVIS agents.

    Agents stay lightweight until a capability needs its own runtime.
    Later a coding agent can wrap Codex, a browser agent can wrap Playwright,
    and a research agent can use dedicated research tooling without changing
    the orchestrator contract.
    """

    def __init__(self, model_router, tool_registry):
        self.model_router = model_router
        self.tools = tool_registry
        self._agents = {}
        self._register_defaults()

    def register(self, agent):
        self._agents[agent.name] = agent

    def get(self, name):
        return self._agents[name]

    def all(self):
        return list(self._agents.values())

    def _register_defaults(self):
        self.register(
            ModelAgent(
                name="general",
                intents={"conversation", "system"},
                instructions="""
You are the general JARVIS agent. Answer clearly and use tools for real
system information instead of inventing results.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ModelAgent(
                name="file_intelligence",
                intents={"file"},
                instructions="""
You are the JARVIS File Intelligence Agent. Prefer actual filesystem tools.
Never claim a file exists, was opened, or was modified unless a tool confirms
it. Use the user's descriptive context to identify likely files.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ModelAgent(
                name="productivity",
                intents={"productivity"},
                instructions="""
You are the JARVIS Productivity Agent. Focus on goals, schedules, deadlines,
learning progress, prioritization, and actionable next steps. Never claim a
reminder or calendar action was created unless an execution tool confirms it.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ModelAgent(
                name="research",
                intents={"research"},
                instructions="""
You are the JARVIS Research Agent. Separate evidence from inference, prefer
primary sources when tools are available, track uncertainty, and do not claim
fresh internet research unless a browsing or research tool actually ran.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ModelAgent(
                name="coding",
                intents={"coding"},
                instructions="""
You are the JARVIS Coding Agent. Inspect before editing, make the smallest
coherent change, preserve existing architecture, test when possible, and never
claim code was changed or tests passed unless tools confirm it.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ModelAgent(
                name="ui_design",
                intents={"ui_design"},
                instructions="""
You are the JARVIS UI Agent. Understand the product and existing interface
before proposing changes. Optimize hierarchy, usability, consistency, and
implementation feasibility rather than producing decorative AI-looking UI.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )
