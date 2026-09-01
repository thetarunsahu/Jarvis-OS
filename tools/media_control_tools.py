from __future__ import annotations

import ctypes
import platform
import time
from typing import Any


class MediaControlTools:
    """Local Windows global media-key controls.

    These commands work with applications that participate in the Windows media
    session, such as many music players and browser media tabs. The media-key API
    does not report the resulting playback state, so results are intentionally
    marked unverified rather than pretending a track/state was confirmed.
    """

    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3
    KEYEVENTF_KEYUP = 0x0002

    @classmethod
    def play_pause(cls) -> dict[str, Any]:
        cls._press(cls.VK_MEDIA_PLAY_PAUSE)
        return {
            "action": "play_pause",
            "verified": False,
            "message": "Sent the Windows play/pause media command.",
        }

    @classmethod
    def next_track(cls) -> dict[str, Any]:
        cls._press(cls.VK_MEDIA_NEXT_TRACK)
        return {
            "action": "next_track",
            "verified": False,
            "message": "Sent the Windows next-track media command.",
        }

    @classmethod
    def previous_track(cls) -> dict[str, Any]:
        cls._press(cls.VK_MEDIA_PREV_TRACK)
        return {
            "action": "previous_track",
            "verified": False,
            "message": "Sent the Windows previous-track media command.",
        }

    @classmethod
    def stop(cls) -> dict[str, Any]:
        cls._press(cls.VK_MEDIA_STOP)
        return {
            "action": "stop",
            "verified": False,
            "message": "Sent the Windows stop-media command.",
        }

    @classmethod
    def _press(cls, virtual_key: int) -> None:
        if platform.system() != "Windows":
            raise RuntimeError("Media controls currently support Windows only.")

        user32 = ctypes.windll.user32
        user32.keybd_event(virtual_key, 0, 0, 0)
        user32.keybd_event(virtual_key, 0, cls.KEYEVENTF_KEYUP, 0)
        time.sleep(0.01)
