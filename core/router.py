from __future__ import annotations

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

        return self.brain.respond(user_input)

    def set_permission_approver(self, approver: Approver | None) -> None:
        self.brain.set_permission_approver(approver)

    @staticmethod
    def greeting() -> str:
        return "Hello. I am JARVIS. How can I help you?"

    @staticmethod
    def help() -> str:
        return (
            "Currently available commands:\n"
            "  • hello\n"
            "  • time\n"
            "  • system info\n"
            "  • list files\n"
            "  • remember key = value\n"
            "  • recall key\n"
            "  • forget key\n"
            "  • memories\n"
            "  • clear conversation\n"
            "  • exit"
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
