import json
from pathlib import Path
from threading import RLock


class AuditLogger:
    """Local JSONL audit trail for important JARVIS events.

    Potentially sensitive payload values are redacted by default. The goal is
    to make autonomous behavior debuggable without turning logs into another
    copy of the user's private data.
    """

    sensitive_markers = (
        "result",
        "content",
        "secret",
        "token",
        "password",
        "api_key",
    )

    def __init__(self, event_bus, path=None):
        project_root = Path(__file__).resolve().parents[1]
        self.path = Path(path or project_root / "logs" / "audit.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        event_bus.subscribe("*", self.record)

    def record(self, event):
        payload = {
            key: self._redact(key, value)
            for key, value in event.payload.items()
        }
        entry = {
            "timestamp": event.created_at,
            "event": event.name,
            "payload": payload,
        }

        with self._lock:
            with open(self.path, "a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _redact(self, key, value):
        lowered = key.lower()
        if any(marker in lowered for marker in self.sensitive_markers):
            return "<redacted>"
        return value
