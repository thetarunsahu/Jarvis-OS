from __future__ import annotations

from functools import partial

from core.workspace import WorkspaceContext
from tools.file_tools import FileTools
from tools.tool_registry import ToolRegistry, ToolSpec


def register_file_tools(
    registry: ToolRegistry,
    workspace: WorkspaceContext | None = None,
) -> None:
    """Attach bounded read-only file inspection tools to a registry."""

    active_workspace = workspace or WorkspaceContext.from_cwd()
    existing = set(registry.get_tool_names())

    list_spec = ToolSpec(
        name="list_files",
        description=(
            "List files and directories inside the active JARVIS workspace using "
            "bounded structured output."
        ),
        handler=partial(
            FileTools.list_files,
            workspace_root=active_workspace.root,
        ),
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Workspace-relative directory to inspect. Defaults to '.'.",
                },
                "max_entries": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": FileTools.MAX_LIST_ENTRIES,
                    "description": "Maximum visible entries to return.",
                },
            },
            "additionalProperties": False,
        },
    )

    read_spec = ToolSpec(
        name="read_text_file",
        description=(
            "Read a UTF-8 text file from the active JARVIS workspace with a strict "
            "size limit. Use this to inspect project source code, configuration, "
            "logs, and notes without reading arbitrary files elsewhere on the computer."
        ),
        handler=partial(
            FileTools.read_text_file,
            workspace_root=active_workspace.root,
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace-relative path of the text file to read.",
                },
                "max_bytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": FileTools.MAX_TEXT_BYTES,
                    "description": (
                        "Maximum bytes to read. Defaults to the JARVIS safety limit."
                    ),
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    registry.register(list_spec, replace="list_files" in existing)
    if read_spec.name not in existing:
        registry.register(read_spec)
