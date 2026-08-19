from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from security.permissions import (
    Approver,
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    PermissionRequest,
)
from tools.app_tools import AppTools
from tools.file_tools import FileTools
from tools.system_tools import SystemTools


ToolHandler = Callable[..., Any]
EventHandler = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: ToolHandler
    parameters: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
    )
    permission: PermissionLevel = PermissionLevel.SAFE
    permission_reason: str = ""

    def as_ollama_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registers tools, exposes model schemas, and enforces permissions."""

    def __init__(
        self,
        permission_manager: PermissionManager | None = None,
        event_handler: EventHandler | None = None,
    ) -> None:
        self.permission_manager = permission_manager or PermissionManager()
        self.event_handler = event_handler
        self._tools: dict[str, ToolSpec] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.register(
            ToolSpec(
                name="list_files",
                description=(
                    "List files and directories in the current JARVIS project "
                    "directory."
                ),
                handler=FileTools.list_files,
            )
        )
        self.register(
            ToolSpec(
                name="system_info",
                description=(
                    "Get information about the computer operating system and "
                    "hardware."
                ),
                handler=SystemTools.get_system_info,
            )
        )
        self.register(
            ToolSpec(
                name="current_time",
                description="Get the current local time.",
                handler=SystemTools.get_time,
            )
        )
        self.register(
            ToolSpec(
                name="list_running_apps",
                description=(
                    "Inspect currently running desktop processes/applications. "
                    "Use this when the user asks what apps are open or running."
                ),
                handler=AppTools.list_running_apps,
                parameters={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "description": "Maximum number of unique processes to return.",
                        }
                    },
                    "additionalProperties": False,
                },
            )
        )
        self.register(
            ToolSpec(
                name="open_app",
                description=(
                    "Open an installed desktop application such as VS Code, "
                    "Chrome, Edge, Notepad, Calculator, Explorer, PowerShell, "
                    "Windows Terminal, or CMD."
                ),
                handler=AppTools.open_app,
                parameters={
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Application name to open.",
                        }
                    },
                    "required": ["app_name"],
                    "additionalProperties": False,
                },
                permission=PermissionLevel.CONFIRM,
                permission_reason="Opening a desktop application changes the user's session.",
            )
        )
        self.register(
            ToolSpec(
                name="open_path",
                description=(
                    "Open an existing local file or folder using the operating "
                    "system's default application."
                ),
                handler=AppTools.open_path,
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Existing local file or folder path to open.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                permission=PermissionLevel.CONFIRM,
                permission_reason="Opening a local file or folder is a desktop action.",
            )
        )
        self.register(
            ToolSpec(
                name="open_project",
                description=(
                    "Open an existing project directory in Visual Studio Code."
                ),
                handler=AppTools.open_project,
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Existing project directory path.",
                        }
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                permission=PermissionLevel.CONFIRM,
                permission_reason="Opening a project launches VS Code and changes the desktop session.",
            )
        )

    def register(self, spec: ToolSpec, *, replace: bool = False) -> None:
        if spec.name in self._tools and not replace:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def set_permission_approver(self, approver: Approver | None) -> None:
        self.permission_manager.set_approver(approver)

    def set_event_handler(self, event_handler: EventHandler | None) -> None:
        self.event_handler = event_handler

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._tools.get(tool_name)
        arguments = arguments or {}

        if spec is None:
            return {
                "ok": False,
                "tool": tool_name,
                "status": "unknown_tool",
                "error": f"Unknown tool: {tool_name}",
            }

        if spec.permission != PermissionLevel.SAFE:
            request = PermissionRequest(
                tool_name=spec.name,
                arguments=arguments,
                level=spec.permission,
                reason=(
                    spec.permission_reason
                    or "This tool requires explicit user approval."
                ),
            )
            self._emit(
                "permission_required",
                tool_name=spec.name,
                arguments=arguments,
                level=spec.permission.value,
                reason=request.reason,
            )

            decision = self.permission_manager.authorize(request)
            if decision != PermissionDecision.ALLOW:
                self._emit(
                    "permission_denied",
                    tool_name=spec.name,
                    level=spec.permission.value,
                )
                return {
                    "ok": False,
                    "tool": spec.name,
                    "status": "permission_denied",
                    "error": "User approval was not granted.",
                }

            self._emit(
                "permission_granted",
                tool_name=spec.name,
                level=spec.permission.value,
            )

        try:
            result = spec.handler(**arguments)
        except Exception as error:
            self._emit(
                "tool_execution_error",
                tool_name=spec.name,
                error_type=type(error).__name__,
                message=str(error),
            )
            return {
                "ok": False,
                "tool": spec.name,
                "status": "execution_error",
                "error": str(error),
            }

        return {
            "ok": True,
            "tool": spec.name,
            "status": "completed",
            "data": result,
        }

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [spec.as_ollama_definition() for spec in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_tool_metadata(self) -> list[dict[str, str]]:
        return [
            {
                "name": spec.name,
                "permission": spec.permission.value,
                "description": spec.description,
            }
            for spec in self._tools.values()
        ]

    def _emit(self, event_name: str, **payload: Any) -> None:
        if self.event_handler is not None:
            self.event_handler(event_name, payload)
