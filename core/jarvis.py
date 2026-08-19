from __future__ import annotations

from core.events import EventBus
from core.orchestrator import JarvisOrchestrator
from security.permissions import Approver, PermissionDecision, PermissionRequest


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

    def set_permission_approver(self, approver: Approver | None) -> None:
        """Attach a client-specific approval callback for side-effecting tools."""
        self.orchestrator.set_permission_approver(approver)

    def start(self) -> None:
        """Run the terminal interface using the shared orchestrator."""
        self.set_permission_approver(self._cli_permission_approver)

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

    @staticmethod
    def _cli_permission_approver(
        request: PermissionRequest,
    ) -> PermissionDecision:
        print("\nJARVIS PERMISSION REQUEST")
        print(f"Tool   : {request.tool_name}")
        print(f"Risk   : {request.level.value}")
        print(f"Reason : {request.reason}")
        if request.arguments:
            print(f"Args   : {request.arguments}")

        answer = input("Allow this action? [y/N]: ").strip().lower()
        if answer in {"y", "yes"}:
            return PermissionDecision.ALLOW
        return PermissionDecision.DENY
