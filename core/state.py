from enum import Enum


class JarvisState(str, Enum):
    """Runtime states shared by the core, voice layer, and UI."""

    OFFLINE = "OFFLINE"
    READY = "READY"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    AWAITING_PERMISSION = "AWAITING_PERMISSION"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"
