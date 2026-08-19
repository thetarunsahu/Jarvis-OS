from __future__ import annotations

import ctypes
import os
import platform
import subprocess
import time
from typing import Any


class SystemControlTools:
    """Windows desktop/session controls.

    Higher layers are responsible for permissions. This module avoids shell=True
    and keeps destructive actions explicit and easy to audit.
    """

    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    KEYEVENTF_KEYUP = 0x0002

    _SETTINGS_SECTIONS = {
        "": "",
        "home": "",
        "display": "display",
        "sound": "sound",
        "bluetooth": "bluetooth",
        "network": "network-status",
        "apps": "appsfeatures",
        "privacy": "privacy",
        "windows update": "windowsupdate",
        "update": "windowsupdate",
    }

    @classmethod
    def volume_up(cls, steps: int = 2) -> dict[str, Any]:
        cls._require_windows()
        count = cls._normalise_steps(steps)
        cls._press_media_key(cls.VK_VOLUME_UP, count)
        return {
            "direction": "up",
            "steps": count,
            "message": f"Raised system volume by {count} media-key step(s).",
        }

    @classmethod
    def volume_down(cls, steps: int = 2) -> dict[str, Any]:
        cls._require_windows()
        count = cls._normalise_steps(steps)
        cls._press_media_key(cls.VK_VOLUME_DOWN, count)
        return {
            "direction": "down",
            "steps": count,
            "message": f"Lowered system volume by {count} media-key step(s).",
        }

    @classmethod
    def set_volume(cls, percent: int) -> dict[str, Any]:
        """Set volume approximately using Windows media keys.

        Windows' media-key API does not expose the actual endpoint level, so this
        intentionally reports verification as false rather than pretending that
        an exact value was measured.
        """

        cls._require_windows()
        target = max(0, min(int(percent), 100))

        # Drive the endpoint to the bottom, then raise in the normal ~2% Windows
        # media-key increments. This avoids another native dependency.
        cls._press_media_key(cls.VK_VOLUME_DOWN, 50)
        up_presses = round(target / 2)
        if up_presses:
            cls._press_media_key(cls.VK_VOLUME_UP, up_presses)

        estimated = min(100, up_presses * 2)
        return {
            "requested_percent": target,
            "estimated_percent": estimated,
            "verified": False,
            "message": (
                f"Adjusted system volume to approximately {estimated}%. "
                "Exact endpoint verification is not available in this backend yet."
            ),
        }

    @classmethod
    def toggle_mute(cls) -> dict[str, Any]:
        cls._require_windows()
        cls._press_media_key(cls.VK_VOLUME_MUTE, 1)
        return {
            "message": "Toggled system mute state.",
            "verified": False,
        }

    @classmethod
    def open_settings(cls, section: str = "") -> dict[str, str]:
        cls._require_windows()
        key = section.strip().lower()
        if key not in cls._SETTINGS_SECTIONS:
            allowed = ", ".join(name or "home" for name in cls._SETTINGS_SECTIONS)
            raise ValueError(f"Unsupported settings section. Allowed: {allowed}")

        suffix = cls._SETTINGS_SECTIONS[key]
        uri = "ms-settings:" + suffix
        os.startfile(uri)  # type: ignore[attr-defined]
        return {
            "section": section or "home",
            "uri": uri,
            "message": f"Opened Windows Settings ({section or 'home'}).",
        }

    @classmethod
    def lock_pc(cls) -> dict[str, Any]:
        cls._require_windows()
        result = bool(ctypes.windll.user32.LockWorkStation())
        if not result:
            raise RuntimeError("Windows refused the workstation lock request.")
        return {
            "locked": True,
            "message": "Locked the workstation.",
        }

    @classmethod
    def shutdown_computer(cls, delay_seconds: int = 30) -> dict[str, Any]:
        cls._require_windows()
        delay = cls._normalise_delay(delay_seconds)
        cls._run_shutdown_command(["/s", "/t", str(delay), "/c", "JARVIS requested shutdown"])
        return {
            "action": "shutdown",
            "delay_seconds": delay,
            "message": f"Shutdown scheduled in {delay} second(s).",
        }

    @classmethod
    def restart_computer(cls, delay_seconds: int = 30) -> dict[str, Any]:
        cls._require_windows()
        delay = cls._normalise_delay(delay_seconds)
        cls._run_shutdown_command(["/r", "/t", str(delay), "/c", "JARVIS requested restart"])
        return {
            "action": "restart",
            "delay_seconds": delay,
            "message": f"Restart scheduled in {delay} second(s).",
        }

    @classmethod
    def cancel_power_action(cls) -> dict[str, Any]:
        cls._require_windows()
        completed = subprocess.run(
            ["shutdown", "/a"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if completed.returncode == 0:
            return {
                "cancelled": True,
                "message": "Cancelled the pending shutdown or restart.",
            }
        return {
            "cancelled": False,
            "message": "No pending shutdown or restart could be cancelled.",
        }

    @classmethod
    def _press_media_key(cls, virtual_key: int, presses: int) -> None:
        user32 = ctypes.windll.user32
        for _ in range(presses):
            user32.keybd_event(virtual_key, 0, 0, 0)
            user32.keybd_event(virtual_key, 0, cls.KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)

    @staticmethod
    def _normalise_steps(steps: int) -> int:
        count = int(steps)
        if count < 1 or count > 20:
            raise ValueError("steps must be between 1 and 20")
        return count

    @staticmethod
    def _normalise_delay(delay_seconds: int) -> int:
        delay = int(delay_seconds)
        if delay < 0 or delay > 3600:
            raise ValueError("delay_seconds must be between 0 and 3600")
        return delay

    @staticmethod
    def _require_windows() -> None:
        if platform.system() != "Windows":
            raise RuntimeError("This system-control tool currently supports Windows only.")

    @staticmethod
    def _run_shutdown_command(arguments: list[str]) -> None:
        completed = subprocess.run(
            ["shutdown", *arguments],
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if completed.returncode != 0:
            error = (completed.stderr or completed.stdout or "shutdown command failed").strip()
            raise RuntimeError(error)
