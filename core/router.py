from datetime import datetime


class CommandRouter:

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

    def current_time(self):
        current_time = datetime.now().strftime("%I:%M:%S %p")
        return f"The current time is {current_time}."

    def identity(self):
        return "I am JARVIS, your personal AI system."

        