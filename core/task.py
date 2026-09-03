from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class TaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    """Structured representation of work inside JARVIS."""

    raw_input: str
    intent: str = "conversation"
    complexity: int = 1
    requires_tools: bool = False
    background: bool = False
    preferred_provider: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    result: Optional[str] = None
    error: Optional[str] = None

    def set_status(self, status):
        self.status = TaskStatus(status)
        self.updated_at = utc_now_iso()

    def complete(self, result=None):
        self.result = None if result is None else str(result)
        self.error = None
        self.set_status(TaskStatus.COMPLETED)

    def fail(self, error):
        self.error = str(error)
        self.set_status(TaskStatus.FAILED)
