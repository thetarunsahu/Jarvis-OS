from __future__ import annotations

from tools.file_tools import FileTools
from tools.tool_registry import ToolRegistry, ToolSpec


def register_file_tools(registry: ToolRegistry) -> None:
    """Attach bounded read-only file inspection tools to a registry."""

    existing = set(registry.get_tool_names())
    spec = ToolSpec(
        name="read_text_file",
        description=(
            "Read a UTF-8 text file from the active JARVIS workspace with a strict "
            "size limit. Use this to inspect project source code, configuration, "
            "logs, and notes without reading arbitrary files elsewhere on the computer."
        ),
        handler=FileTools.read_text_file,
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

    if spec.name not in existing:
        registry.register(spec)
