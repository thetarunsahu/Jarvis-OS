from core.brain import Brain
from memory.memory_manager import MemoryManager
from tools.file_tools import FileTools
from tools.system_tools import SystemTools


class CommandRouter:
    def __init__(self):
        self.memory = MemoryManager()
        self.brain = Brain()

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

        if command in ["tasks", "show tasks", "list tasks"]:
            return self.list_tasks()

        if command.startswith("task "):
            return self.task_status(user_input[5:].strip())

        if command == "memories":
            return self.memory.get_all()

        if command.startswith("remember "):
            content = user_input[9:].strip()

            if "=" in content:
                key, value = content.split("=", 1)
                return self.memory.remember(key.strip(), value.strip())

            return "Use: remember key = value"

        if command.startswith("recall "):
            key = user_input[7:].strip()
            return self.memory.recall(key)

        if command.startswith("forget "):
            key = user_input[7:].strip()
            return self.memory.forget(key)

        return self.brain.respond(user_input)

    def greeting(self):
        return "Hello. I am JARVIS. How can I help you?"

    def help(self):
        return (
            "Currently available commands:\n"
            "  • hello\n"
            "  • time\n"
            "  • system info\n"
            "  • list files\n"
            "  • tasks\n"
            "  • task <id>\n"
            "  • remember key = value\n"
            "  • recall <key>\n"
            "  • forget <key>\n"
            "  • who are you\n"
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

    def list_tasks(self):
        tasks = self.brain.list_tasks(limit=10)
        if not tasks:
            return "No JARVIS tasks have been recorded yet."

        lines = []
        for task in tasks:
            lines.append(
                f"{task.task_id[:8]}  {task.status.value:<16} "
                f"{task.intent:<12}  {task.raw_input[:60]}"
            )
        return "Recent tasks:\n" + "\n".join(lines)

    def task_status(self, task_reference):
        task = self.brain.get_task(task_reference)
        if task is None:
            return f"I could not find a unique task matching '{task_reference}'."

        details = [
            f"Task: {task.task_id}",
            f"Intent: {task.intent}",
            f"Status: {task.status.value}",
            f"Background: {task.background}",
        ]
        if task.result:
            details.append(f"Result: {task.result}")
        if task.error:
            details.append(f"Error: {task.error}")
        return "\n".join(details)
