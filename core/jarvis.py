from __future__ import annotations

from core.events import EventBus
from core.orchestrator import JarvisOrchestrator


class Jarvis:
    """Public JARVIS application service used by CLI, GUI, and voice clients."""

    def __init__(self) -> None:
        self.name = "JARVIS"
        self.version = "0.2.0-dev"
        self.events = EventBus()
        self.orchestrator = JarvisOrchestrator(events=self.events)

    @property
    def state(self):
        return self.orchestrator.state

    def process(self, user_input: str) -> str:
        return self.orchestrator.process(user_input)

    def start(self) -> None:
        """Run the legacy terminal interface.

        The CLI is intentionally thin: all request handling goes through the
        same orchestrator that the desktop HUD and voice interface will use.
        """
        print("=" * 50)
        print("                 J A R V I S")
        print("=" * 50)
        print(f"Version: {self.version}")
        print("Status : ONLINE")
        print("Type 'help' for commands.")
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
