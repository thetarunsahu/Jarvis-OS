from agents.model_agent import ModelAgent
from agents.research_agent import ResearchAgent


class AgentRegistry:
    """Registry of specialist JARVIS agents.

    Agents stay lightweight until a capability needs its own runtime. Specialist
    runtimes can be added behind an agent without changing the orchestrator.
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
                intents={"conversation", "system", "application"},
                instructions="""
You are the general JARVIS agent. For ordinary conversation, explanations,
ideas, facts, brainstorming, and general knowledge, answer directly and
naturally from the model. Do not refuse merely because no tool exists; tools
are only required when the request depends on real computer state or asks for
an actual action. For real system information and actions, use tools instead
of inventing results. For application-launch requests, use
list_applications/open_application and only claim success when the tool confirms
it. Keep conversational replies concise and human unless the user asks for
more detail.
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
You are the JARVIS File Intelligence Agent. Prefer the file-index and actual
filesystem tools. Never claim a file exists, was opened, or was modified unless
a tool confirms it. Use descriptive context and ranked file candidates rather
than requiring the user to remember exact filenames.
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
learning progress, prioritization, and actionable next steps. Use stored goals,
reminders, and the daily brief when useful. Never claim a reminder or goal was
created or changed unless an execution tool confirms it.
""",
                model_router=self.model_router,
                tool_registry=self.tools,
            )
        )

        self.register(
            ResearchAgent(
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
claim code was changed or tests passed unless tools confirm it. A dedicated
coding runtime can replace this generic model runtime later.
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
