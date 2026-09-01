from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class Task:
    """Structured representation of a user request inside JARVIS."""

    raw_input: str
    intent: str = "conversation"
    complexity: int = 1
    requires_tools: bool = False
    background: bool = False
    preferred_provider: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid4()))
