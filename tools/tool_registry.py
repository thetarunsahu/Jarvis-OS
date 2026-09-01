from dataclasses import dataclass
from typing import Callable, Optional

from core.policy_engine import PermissionLevel, PolicyEngine
from tools.file_intelligence_tools import FileIntelligenceTools
from tools.file_tools import FileTools
from tools.productivity_tools import ProductivityTools
from tools.system_tools import SystemTools


@dataclass
class ToolSpec:
    name: str
    handler: Callable
    description: str
    permission_level: PermissionLevel = PermissionLevel.READ
    parameters: Optional[dict] = None

    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
                or {
                    "type": "object",
                    "properties": {},
                },
            },
        }


class ToolRegistry:
    """Registry of executable actions protected by PolicyEngine."""

    def __init__(
        self,
        policy_engine=None,
        productivity_tools=None,
        file_intelligence_tools=None,
    ):
        self.policy = policy_engine or PolicyEngine()
        self.productivity = productivity_tools or ProductivityTools()
        self.file_intelligence = file_intelligence_tools or FileIntelligenceTools()
        self.tools = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(
            ToolSpec(
                name="list_files",
                handler=FileTools.list_files,
                description=(
                    "List files and directories in the current "
                    "JARVIS project directory."
                ),
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="system_info",
                handler=SystemTools.get_system_info,
                description=(
                    "Get information about the computer operating "
                    "system and hardware."
                ),
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="current_time",
                handler=SystemTools.get_time,
                description="Get the current local clock time.",
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="current_datetime",
                handler=SystemTools.get_datetime,
                description=(
                    "Get the current local date, time, and timezone as "
                    "an ISO-8601 timestamp. Use this before converting "
                    "relative reminder times such as 'tomorrow evening'."
                ),
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="index_files",
                handler=self.file_intelligence.index_files,
                description=(
                    "Refresh JARVIS's local searchable file index for the "
                    "configured index roots. Use this before descriptive file "
                    "search when the index may be stale."
                ),
                permission_level=PermissionLevel.SAFE,
            )
        )
        self.register(
            ToolSpec(
                name="search_files",
                handler=self.file_intelligence.search_files,
                description=(
                    "Search indexed local files by filename, path, or extracted "
                    "text using descriptive words instead of requiring an exact "
                    "filename."
                ),
                permission_level=PermissionLevel.READ,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Words describing the file to find.",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            )
        )
        self.register(
            ToolSpec(
                name="file_index_status",
                handler=self.file_intelligence.file_index_status,
                description=(
                    "Show how many files JARVIS has indexed and which roots "
                    "are currently configured."
                ),
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="create_goal",
                handler=self.productivity.create_goal,
                description="Create a personal goal for the user.",
                permission_level=PermissionLevel.SAFE,
                parameters={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Clear goal title.",
                        },
                        "target_date": {
                            "type": "string",
                            "description": "Optional ISO-8601 target date or datetime.",
                        },
                    },
                    "required": ["title"],
                },
            )
        )
        self.register(
            ToolSpec(
                name="list_goals",
                handler=self.productivity.list_goals,
                description="List the user's active personal goals.",
                permission_level=PermissionLevel.READ,
            )
        )
        self.register(
            ToolSpec(
                name="create_reminder",
                handler=self.productivity.create_reminder,
                description=(
                    "Create a persistent reminder. due_at must be a "
                    "timezone-aware ISO-8601 timestamp. For relative times, "
                    "call current_datetime first and resolve the date/time."
                ),
                permission_level=PermissionLevel.SAFE,
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "What the user should be reminded about.",
                        },
                        "due_at": {
                            "type": "string",
                            "description": "Timezone-aware ISO-8601 reminder datetime.",
                        },
                    },
                    "required": ["text", "due_at"],
                },
            )
        )
        self.register(
            ToolSpec(
                name="list_reminders",
                handler=self.productivity.list_reminders,
                description="List pending reminders ordered by due time.",
                permission_level=PermissionLevel.READ,
            )
        )

    def register(self, spec):
        self.tools[spec.name] = spec

    def execute(self, tool_name, arguments=None, approved=False):
        spec = self.tools.get(tool_name)

        if spec is None:
            return f"Unknown tool: {tool_name}"

        decision = self.policy.evaluate(
            action=tool_name,
            permission_level=spec.permission_level,
            approved=approved,
        )

        if not decision.allowed:
            return f"Confirmation required: {decision.reason}"

        try:
            arguments = arguments or {}
            return spec.handler(**arguments)
        except TypeError as error:
            return f"Invalid tool arguments for {tool_name}: {error}"
        except Exception as error:
            return f"Tool execution failed: {error}"

    def get_tool_definitions(self):
        return [spec.definition() for spec in self.tools.values()]

    def get_tool_names(self):
        return list(self.tools.keys())
