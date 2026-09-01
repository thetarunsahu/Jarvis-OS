from dataclasses import dataclass

from core.policy_engine import PermissionLevel, PolicyEngine
from tools.file_tools import FileTools
from tools.system_tools import SystemTools


@dataclass
class ToolSpec:
    name: str
    handler: callable
    description: str
    permission_level: PermissionLevel = PermissionLevel.READ
    parameters: dict = None

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
    """Registry of executable system tools protected by PolicyEngine."""

    def __init__(self, policy_engine=None):
        self.policy = policy_engine or PolicyEngine()
        self.tools = {}

        self.register(
            ToolSpec(
                name="list_files",
                handler=self.list_files,
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
                handler=self.system_info,
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
                handler=self.current_time,
                description="Get the current local time.",
                permission_level=PermissionLevel.READ,
            )
        )

    def register(self, spec):
        self.tools[spec.name] = spec

    def list_files(self):
        return FileTools.list_files()

    def system_info(self):
        return SystemTools.get_system_info()

    def current_time(self):
        return SystemTools.get_time()

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
        except TypeError:
            return spec.handler()
        except Exception as error:
            return f"Tool execution failed: {error}"

    def get_tool_definitions(self):
        return [spec.definition() for spec in self.tools.values()]

    def get_tool_names(self):
        return list(self.tools.keys())
