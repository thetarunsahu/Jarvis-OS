from dataclasses import dataclass
from typing import Callable, Optional

from core.approval_manager import ApprovalManager
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
        approval_manager=None,
    ):
        self.policy = policy_engine or PolicyEngine()
        self.productivity = productivity_tools or ProductivityTools()
        self.file_intelligence = file_intelligence_tools or FileIntelligenceTools()
        self.approvals = approval_manager or ApprovalManager()
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
                name="update_goal",
                handler=self.productivity.update_goal,
                description=(
                    "Update a stored goal's progress percentage or status. Use "
                    "this when the user reports progress or completes a goal."
                ),
                permission_level=PermissionLevel.SAFE,
                parameters={
                    "type": "object",
                    "properties": {
                        "goal_id": {"type": "string"},
                        "progress": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "status": {"type": "string"},
                    },
                    "required": ["goal_id"],
                },
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
        self.register(
            ToolSpec(
                name="complete_reminder",
                handler=self.productivity.complete_reminder,
                description="Mark a stored reminder as completed.",
                permission_level=PermissionLevel.SAFE,
                parameters={
                    "type": "object",
                    "properties": {
                        "reminder_id": {"type": "string"},
                    },
                    "required": ["reminder_id"],
                },
            )
        )
        self.register(
            ToolSpec(
                name="daily_brief",
                handler=self.productivity.daily_brief,
                description=(
                    "Generate an evidence-based accountability brief from active "
                    "goals, reminders, and recent JARVIS task history."
                ),
                permission_level=PermissionLevel.READ,
            )
        )

    def register(self, spec):
        self.tools[spec.name] = spec

    def execute(self, tool_name, arguments=None, approved=False):
        spec = self.tools.get(tool_name)

        if spec is None:
            return f"Unknown tool: {tool_name}"

        arguments = arguments or {}
        decision = self.policy.evaluate(
            action=tool_name,
            permission_level=spec.permission_level,
            approved=approved,
        )

        if not decision.allowed:
            request = self.approvals.create(
                action=tool_name,
                arguments=arguments,
                permission_level=spec.permission_level,
                reason=decision.reason,
            )
            return (
                f"Approval required [{request['approval_id'][:8]}]: "
                f"{decision.reason} Use 'approve {request['approval_id'][:8]}' "
                "or 'deny <id>'."
            )

        try:
            return spec.handler(**arguments)
        except TypeError as error:
            return f"Invalid tool arguments for {tool_name}: {error}"
        except Exception as error:
            return f"Tool execution failed: {error}"

    def list_pending_approvals(self, limit=20):
        return self.approvals.list(status="pending", limit=limit)

    def resolve_approval(self, reference, approved):
        request = self.approvals.find(reference)
        if request is None:
            return f"No unique approval request matches '{reference}'."

        if request["status"] != "pending":
            return (
                f"Approval {request['approval_id'][:8]} is already "
                f"{request['status']}."
            )

        if not approved:
            self.approvals.resolve(request["approval_id"], "denied")
            return f"Denied approval {request['approval_id'][:8]} for {request['action']}."

        result = self.execute(
            request["action"],
            arguments=request["arguments"],
            approved=True,
        )
        status = "failed" if str(result).startswith(("Tool execution failed", "Invalid tool")) else "executed"
        self.approvals.resolve(request["approval_id"], status, result=result)
        return result

    def get_tool_definitions(self):
        return [spec.definition() for spec in self.tools.values()]

    def get_tool_names(self):
        return list(self.tools.keys())
