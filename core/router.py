from __future__ import annotations

import re
from typing import Any

from core.brain import Brain
from core.events import EventBus
from memory.memory_manager import MemoryManager
from security.permissions import Approver
from tools.file_tools import FileTools
from tools.system_tools import SystemTools


class CommandRouter:
    """Handles deterministic local commands, then falls back to the AI brain."""

    def __init__(
        self,
        memory: MemoryManager | None = None,
        brain: Brain | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.memory = memory or MemoryManager()
        self.brain = brain or Brain(events=events)

    def route(self, user_input: str):
        command = user_input.lower().strip()

        if command in {"hello", "hi", "hey"}:
            return self.greeting()

        if command in {"help", "commands"}:
            return self.help()

        if command in {"time", "what time is it", "current time"}:
            return self.current_time()

        if command in {"who are you", "what are you", "your name"}:
            return self.identity()

        if command in {"system", "system info", "system information"}:
            return self.system_info()

        if command in {"list files", "files", "show files"}:
            return self.list_files()

        if command == "memories":
            return self.memory.get_all()

        if command.startswith("remember "):
            content = user_input[9:].strip()
            if "=" not in content:
                return "Use: remember key = value"

            key, value = content.split("=", 1)
            return self.memory.remember(key.strip(), value.strip())

        if command.startswith("recall "):
            key = user_input[7:].strip()
            return self.memory.recall(key)

        if command.startswith("forget "):
            key = user_input[7:].strip()
            return self.memory.forget(key)

        if command in {"clear conversation", "clear chat", "reset conversation"}:
            self.brain.clear_conversation()
            return "Conversation context cleared."

        deterministic = self._route_deterministic_action(user_input)
        if deterministic is not None:
            return deterministic

        return self.brain.respond(user_input)

    def set_permission_approver(self, approver: Approver | None) -> None:
        self.brain.set_permission_approver(approver)

    def _route_deterministic_action(self, user_input: str) -> str | None:
        """Execute high-confidence local actions without asking the LLM to choose.

        Common desktop commands use a fast lane so obvious actions do not pay the
        language-model latency. Flexible or ambiguous requests still fall back to
        the model and its normal tool loop.
        """

        command = " ".join(user_input.lower().strip().split())

        if command in {
            "what apps are running",
            "what applications are running",
            "which apps are running",
            "which applications are running",
            "show running apps",
            "list running apps",
            "show running applications",
            "list running applications",
        }:
            return self._execute_tool("list_running_apps", {})

        volume_match = re.search(
            r"\b(?:set|change|turn)\s+(?:the\s+)?(?:system\s+)?volume"
            r"(?:\s+(?:to|at))?\s+(\d{1,3})\s*(?:%|percent)?\b",
            command,
        )
        if volume_match:
            percent = int(volume_match.group(1))
            if not 0 <= percent <= 100:
                return "Volume must be between 0 and 100 percent."
            return self._execute_tool("set_volume", {"percent": percent})

        if any(
            phrase in command
            for phrase in (
                "volume up",
                "increase volume",
                "raise volume",
                "turn the volume up",
                "turn volume up",
            )
        ):
            return self._execute_tool("volume_up", {})

        if any(
            phrase in command
            for phrase in (
                "volume down",
                "decrease volume",
                "lower volume",
                "turn the volume down",
                "turn volume down",
            )
        ):
            return self._execute_tool("volume_down", {})

        if command in {
            "mute",
            "mute system",
            "mute the system",
            "toggle mute",
            "toggle system mute",
        }:
            return self._execute_tool("toggle_mute", {})

        settings_sections = {
            "sound": ("sound settings", "audio settings"),
            "display": ("display settings",),
            "bluetooth": ("bluetooth settings",),
            "network": ("network settings", "wifi settings", "wi-fi settings"),
            "apps": ("app settings", "apps settings"),
            "privacy": ("privacy settings",),
            "update": ("windows update", "update settings"),
        }
        for section, phrases in settings_sections.items():
            if any(phrase in command for phrase in phrases) and (
                command.startswith("open ")
                or command.startswith("show ")
                or "settings" in command
            ):
                return self._execute_tool("open_settings", {"section": section})

        if command in {
            "lock pc",
            "lock the pc",
            "lock computer",
            "lock the computer",
            "lock workstation",
            "lock the workstation",
        }:
            return self._execute_tool("lock_pc", {})

        if command in {
            "cancel shutdown",
            "cancel the shutdown",
            "cancel restart",
            "cancel the restart",
            "cancel power action",
        }:
            return self._execute_tool("cancel_power_action", {})

        shutdown_delay = self._extract_power_delay(command, "shutdown")
        if shutdown_delay is not None:
            return self._execute_tool(
                "shutdown_computer",
                {"delay_seconds": shutdown_delay},
            )

        restart_delay = self._extract_power_delay(command, "restart")
        if restart_delay is not None:
            return self._execute_tool(
                "restart_computer",
                {"delay_seconds": restart_delay},
            )

        youtube_match = re.match(
            r"^(?:search\s+youtube\s+(?:for\s+)?|youtube\s+search\s+)(.+)$",
            command,
        )
        if youtube_match:
            query = youtube_match.group(1).strip()
            if query:
                return self._execute_tool("search_youtube", {"query": query})

        web_match = re.match(
            r"^(?:search\s+(?:google|the web|web)\s+(?:for\s+)?|"
            r"google\s+search\s+)(.+)$",
            command,
        )
        if web_match:
            query = web_match.group(1).strip()
            if query:
                return self._execute_tool("search_web", {"query": query})

        open_match = re.match(r"^(?:open|visit|go to)\s+(.+)$", command)
        if open_match:
            target = open_match.group(1).strip()
            if self._looks_like_web_target(target):
                return self._execute_tool("open_url", {"url": target})

        app_match = re.match(r"^(?:open|launch|start)\s+(.+?)(?:\s+app)?$", command)
        if app_match:
            app_name = self._normalise_known_app(app_match.group(1).strip())
            if app_name is not None:
                return self._execute_tool("open_app", {"app_name": app_name})

        return None

    @staticmethod
    def _normalise_known_app(target: str) -> str | None:
        aliases = {
            "notepad": "notepad",
            "calculator": "calculator",
            "calc": "calculator",
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "edge",
            "microsoft edge": "edge",
            "vscode": "vscode",
            "vs code": "vscode",
            "visual studio code": "vscode",
            "explorer": "explorer",
            "file explorer": "explorer",
            "powershell": "powershell",
            "windows powershell": "powershell",
            "terminal": "terminal",
            "windows terminal": "terminal",
            "cmd": "cmd",
            "command prompt": "cmd",
        }
        return aliases.get(target)

    @staticmethod
    def _extract_power_delay(command: str, action: str) -> int | None:
        if not re.search(rf"\b{re.escape(action)}\b", command):
            return None

        starts_action = (
            command == action
            or command.startswith(f"{action} ")
            or command.startswith(f"please {action}")
        )
        if not starts_action:
            return None

        match = re.search(
            r"\bin\s+(\d+)\s*(second|seconds|minute|minutes)\b",
            command,
        )
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            seconds = amount * 60 if unit.startswith("minute") else amount
            return max(0, min(seconds, 3600))

        return 30

    @staticmethod
    def _looks_like_web_target(target: str) -> bool:
        if target.startswith(("http://", "https://")):
            return True
        return bool(
            re.match(
                r"^[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?:/[^\s]*)?$",
                target,
                flags=re.IGNORECASE,
            )
        )

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        result = self.brain.execute_tool(tool_name, arguments)
        if result.get("ok"):
            data = result.get("data")
            if isinstance(data, dict):
                message = data.get("message")
                if message:
                    return str(message)
            if data is None:
                return f"{tool_name} completed."
            return str(data)

        if result.get("status") == "permission_denied":
            return "Action cancelled because permission was not granted."

        error = result.get("error") or "Unknown tool error."
        return f"I couldn't complete that action: {error}"

    @staticmethod
    def greeting() -> str:
        return "Hello. I am JARVIS. How can I help you?"

    @staticmethod
    def help() -> str:
        return (
            "JARVIS supports natural-language commands. Examples:\n"
            "  • system info / what apps are running\n"
            "  • open Notepad / open Chrome / open a local project\n"
            "  • open example.com / search Google for local AI\n"
            "  • search YouTube for Interstellar soundtrack\n"
            "  • volume up / volume down / set volume to 40 percent / mute\n"
            "  • open sound settings / lock the PC\n"
            "  • shutdown or restart (explicit confirmation required)\n"
            "  • cancel pending shutdown or restart\n"
            "  • remember key = value / recall key / forget key / memories\n"
            "  • clear conversation\n"
            "Side-effecting actions require permission before execution."
        )

    @staticmethod
    def system_info() -> str:
        info = SystemTools.get_system_info()
        return (
            f"System: {info['system']}\n"
            f"Release: {info['release']}\n"
            f"Machine: {info['machine']}\n"
            f"Processor: {info['processor']}"
        )

    @staticmethod
    def current_time() -> str:
        return f"The current time is {SystemTools.get_time()}."

    @staticmethod
    def identity() -> str:
        return "I am JARVIS, your personal AI system."

    @staticmethod
    def list_files():
        return FileTools.list_files()
