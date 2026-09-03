from .router import CommandRouter


class Jarvis:
    def __init__(self):
        self.name = "JARVIS"
        self.version = "0.2.0-dev"
        self.router = CommandRouter()

    def start(self):
        print("=" * 50)
        print("                 J A R V I S")
        print("=" * 50)
        print(f"Version: {self.version}")
        print("Status : ONLINE")
        print("Type 'help' for commands.")
        print("Type 'exit' to shutdown.\n")

        try:
            while True:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "exit":
                    print("JARVIS: Shutting down. Good night.")
                    break

                response = self.process(user_input)
                print(f"JARVIS: {response}\n")
        finally:
            self.router.brain.shutdown()

    def process(self, user_input):
        response = self.router.route(user_input)

        if response is not None:
            return response

        return (
            "I don't understand that command yet. "
            "Type 'help' to see what I can currently do."
        )
