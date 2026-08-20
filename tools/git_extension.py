from __future__ import annotations

from functools import partial

from core.workspace import WorkspaceContext
from tools.git_tools import GitTools
from tools.tool_registry import ToolRegistry, ToolSpec


def register_git_tools(
    registry: ToolRegistry,
    workspace: WorkspaceContext | None = None,
) -> None:
    """Attach bounded read-only Git inspection tools to a registry."""

    active_workspace = workspace or WorkspaceContext.from_cwd()
    existing = set(registry.get_tool_names())

    specs = (
        ToolSpec(
            name="git_status",
            description=(
                "Inspect the Git repository at the active JARVIS workspace root. "
                "Returns the current branch, upstream divergence, clean/dirty state, "
                "and a bounded structured list of changed or untracked paths."
            ),
            handler=partial(
                GitTools.inspect_status,
                workspace_root=active_workspace.root,
            ),
            parameters={
                "type": "object",
                "properties": {
                    "max_entries": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": GitTools.MAX_STATUS_ENTRIES,
                        "description": "Maximum changed paths to return.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "description": "Bounded timeout for Git inspection.",
                    },
                },
                "additionalProperties": False,
            },
        ),
        ToolSpec(
            name="git_diff",
            description=(
                "Inspect a bounded Git patch for the active JARVIS workspace. "
                "By default returns unstaged changes; set staged=true to inspect "
                "changes already added to the Git index."
            ),
            handler=partial(
                GitTools.inspect_diff,
                workspace_root=active_workspace.root,
            ),
            parameters={
                "type": "object",
                "properties": {
                    "staged": {
                        "type": "boolean",
                        "description": "When true, inspect staged changes instead of unstaged changes.",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": GitTools.MAX_DIFF_BYTES,
                        "description": "Maximum UTF-8 patch bytes to return.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                        "description": "Bounded timeout for Git inspection.",
                    },
                },
                "additionalProperties": False,
            },
        ),
    )

    for spec in specs:
        if spec.name not in existing:
            registry.register(spec)
