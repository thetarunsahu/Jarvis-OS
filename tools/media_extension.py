from __future__ import annotations

from security.permissions import PermissionLevel
from tools.media_control_tools import MediaControlTools
from tools.tool_registry import ToolRegistry, ToolSpec


def register_media_tools(registry: ToolRegistry) -> None:
    """Attach the media capability pack to an existing ToolRegistry."""

    existing = set(registry.get_tool_names())
    specs = (
        ToolSpec(
            name="media_play_pause",
            description=(
                "Send the Windows global play/pause media command. This toggles "
                "playback and cannot verify the resulting playback state."
            ),
            handler=MediaControlTools.play_pause,
            permission=PermissionLevel.CONFIRM,
            permission_reason="Changing media playback affects the current desktop session.",
        ),
        ToolSpec(
            name="media_next",
            description="Skip to the next track using the Windows global media command.",
            handler=MediaControlTools.next_track,
            permission=PermissionLevel.CONFIRM,
            permission_reason="Changing the current media track affects playback.",
        ),
        ToolSpec(
            name="media_previous",
            description="Go to the previous track using the Windows global media command.",
            handler=MediaControlTools.previous_track,
            permission=PermissionLevel.CONFIRM,
            permission_reason="Changing the current media track affects playback.",
        ),
        ToolSpec(
            name="media_stop",
            description="Stop media playback using the Windows global stop command.",
            handler=MediaControlTools.stop,
            permission=PermissionLevel.CONFIRM,
            permission_reason="Stopping media affects the current desktop session.",
        ),
    )

    for spec in specs:
        if spec.name not in existing:
            registry.register(spec)
