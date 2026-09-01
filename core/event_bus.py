from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable, Dict, List


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)


class EventBus:
    """Small in-process event bus for decoupling JARVIS modules."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._lock = RLock()

    def subscribe(self, event_name, handler):
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name, handler):
        with self._lock:
            handlers = self._subscribers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event_name, **payload):
        event = Event(name=event_name, payload=payload)

        with self._lock:
            handlers = list(self._subscribers.get(event_name, []))
            handlers += list(self._subscribers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                # One observer must never break the system event pipeline.
                continue

        return event
