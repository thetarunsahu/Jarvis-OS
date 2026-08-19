from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class PermissionLevel(str, Enum):
    """Risk level attached to a tool."""

    SAFE = "safe"
    CONFIRM = "confirm"
    DESTRUCTIVE = "destructive"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True)
class PermissionRequest:
    tool_name: str
    arguments: dict[str, Any]
    level: PermissionLevel
    reason: str


Approver = Callable[[PermissionRequest], bool | PermissionDecision]


class PermissionManager:
    """Central policy for deciding whether a tool may execute.

    SAFE tools run automatically. Any higher-risk tool requires an explicit
    approver. If no approver is configured, the action is denied by default.
    """

    def __init__(self, approver: Approver | None = None) -> None:
        self._approver = approver

    def set_approver(self, approver: Approver | None) -> None:
        self._approver = approver

    def authorize(self, request: PermissionRequest) -> PermissionDecision:
        if request.level == PermissionLevel.SAFE:
            return PermissionDecision.ALLOW

        if self._approver is None:
            return PermissionDecision.DENY

        decision = self._approver(request)
        if isinstance(decision, PermissionDecision):
            return decision

        return PermissionDecision.ALLOW if decision else PermissionDecision.DENY
