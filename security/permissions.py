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
    ALLOW_SESSION = "allow_session"
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

    SAFE tools run automatically. CONFIRM tools may be approved once or for the
    current JARVIS session. DESTRUCTIVE tools always require a fresh approval and
    can never be silently trusted for the session.
    """

    def __init__(self, approver: Approver | None = None) -> None:
        self._approver = approver
        self._session_grants: set[str] = set()

    def set_approver(self, approver: Approver | None) -> None:
        self._approver = approver

    def clear_session_grants(self) -> None:
        self._session_grants.clear()

    def is_session_granted(self, tool_name: str) -> bool:
        return tool_name in self._session_grants

    def authorize(self, request: PermissionRequest) -> PermissionDecision:
        if request.level == PermissionLevel.SAFE:
            return PermissionDecision.ALLOW

        if (
            request.level == PermissionLevel.CONFIRM
            and request.tool_name in self._session_grants
        ):
            return PermissionDecision.ALLOW

        if self._approver is None:
            return PermissionDecision.DENY

        raw_decision = self._approver(request)
        if isinstance(raw_decision, PermissionDecision):
            decision = raw_decision
        else:
            decision = (
                PermissionDecision.ALLOW
                if raw_decision
                else PermissionDecision.DENY
            )

        if decision == PermissionDecision.ALLOW_SESSION:
            if request.level == PermissionLevel.CONFIRM:
                self._session_grants.add(request.tool_name)
            return PermissionDecision.ALLOW

        return decision
