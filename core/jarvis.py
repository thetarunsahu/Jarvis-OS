class Jarvis:
    def __init__(self):
        self.name = "JARVIS"
        self.version = "0.1.0"

    def start(self):
        print("=" * 50)
        print("                 J A R V I S")
        print("=" * 50)
        print(f"Version: {self.version}")
        print("Status : ONLINE")
        print("Type 'exit' to shutdown.\n")

        while True:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "exit":
                print("JARVIS: Shutting down. Good night.")
                break

            response = self.process(user_input)
            print(f"JARVIS: {response}\n")

    def process(self, user_input):
        return f"I received: {user_input}"