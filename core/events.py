from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable


@dataclass(frozen=True)
class JarvisEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class EventBus:
    """Small in-process event bus used to decouple the core from UI/voice."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[JarvisEvent], None]]] = {}
        self._lock = RLock()

    def subscribe(self, event_name: str, callback: Callable[[JarvisEvent], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[JarvisEvent], None]) -> None:
        with self._lock:
            callbacks = self._subscribers.get(event_name, [])
            if callback in callbacks:
                callbacks.remove(callback)

    def emit(self, event_name: str, **payload: Any) -> JarvisEvent:
        event = JarvisEvent(name=event_name, payload=payload)

        with self._lock:
            callbacks = list(self._subscribers.get(event_name, []))
            callbacks += list(self._subscribers.get("*", []))

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                # Observers must never be allowed to crash the JARVIS core.
                continue

        return event
