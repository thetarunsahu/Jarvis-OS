from dataclasses import dataclass
from enum import IntEnum


class PermissionLevel(IntEnum):
    READ = 0
    SAFE = 1
    MODIFY = 2
    SENSITIVE = 3
    CRITICAL = 4


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_confirmation: bool
    reason: str


class PolicyEngine:
    """Central permission boundary for actions with real-world side effects."""

    def __init__(self, auto_approve_up_to=PermissionLevel.SAFE):
        self.auto_approve_up_to = PermissionLevel(auto_approve_up_to)

    def evaluate(self, action, permission_level, approved=False):
        level = PermissionLevel(permission_level)

        if approved:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=False,
                reason=f"{action} was explicitly approved.",
            )

        if level <= self.auto_approve_up_to:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=False,
                reason=f"{action} is within the automatic permission boundary.",
            )

        return PolicyDecision(
            allowed=False,
            requires_confirmation=True,
            reason=(
                f"{action} requires confirmation at permission level "
                f"{level.name}."
            ),
        )
