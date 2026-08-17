from datetime import datetime
from tools.system_tools import SystemTools
from tools.file_tools import FileTools
from memory.memory_manager import MemoryManager

class CommandRouter:
    
    def __init__(self):
        self.memory = MemoryManager()
        
    def route(self, user_input):
        command = user_input.lower().strip()

        if command in ["hello", "hi", "hey"]:
            return self.greeting()

        if command in ["help", "commands"]:
            return self.help()

        if command in ["time", "what time is it", "current time"]:
            return self.current_time()

        if command in ["who are you", "what are you", "your name"]:
            return self.identity()
        
        if command in ["system", "system info", "system information"]:
            return self.system_info()
        
        if command in ["list files", "files", "show files"]:
            return self.list_files()
        
        if command == "memories":
            return self.memory.get_all()
        
        if command.startswith("remember "):
            content = user_input[9:].strip()

            if "=" in content:
                key, value = content.split("=", 1)

                return self.memory.remember(
                    key.strip(),
                    value.strip()
                )

            return "Use: remember key = value"

        if command.startswith("recall "):
            key = user_input[7:].strip()
            return self.memory.recall(key)

        if command.startswith("forget "):
            key = user_input[7:].strip()
            return self.memory.forget(key)

        return None

    def greeting(self):
        return "Hello. I am JARVIS. How can I help you?"

    def help(self):
        return (
            "Currently available commands:\n"
            "  • hello\n"
            "  • time\n"
            "  • who are you\n"
            "  • help\n"
            "  • exit"
        )
    
    def system_info(self):
        info = SystemTools.get_system_info()

        return (
            f"System: {info['system']}\n"
            f"Release: {info['release']}\n"
            f"Machine: {info['machine']}\n"
            f"Processor: {info['processor']}"
        )

    def current_time(self):
        return f"The current time is {SystemTools.get_time()}."

    def identity(self):
        return "I am JARVIS, your personal AI system."

    def list_files(self):
        return FileTools.list_files()
    