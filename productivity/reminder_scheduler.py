from threading import Event as ThreadEvent
from threading import Thread

from core.event_bus import EventBus
from productivity.productivity_store import ProductivityStore


class ReminderScheduler:
    """Checks persistent reminders and emits reminder.due events."""

    def __init__(self, store=None, event_bus=None, poll_seconds=15):
        self.store = store or ProductivityStore()
        self.event_bus = event_bus or EventBus()
        self.poll_seconds = max(1, int(poll_seconds))
        self._stop = ThreadEvent()
        self._thread = None

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self.running:
            return

        self._stop.clear()
        self._thread = Thread(
            target=self._loop,
            name="jarvis-reminder-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self, wait=True):
        self._stop.set()
        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.poll_seconds + 1)

    def check_now(self):
        due = self.store.due_reminders()
        for reminder in due:
            self.event_bus.publish(
                "reminder.due",
                reminder_id=reminder["reminder_id"],
                text=reminder["text"],
                due_at=reminder["due_at"],
            )
            self.store.mark_reminder_notified(reminder["reminder_id"])
        return due

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.check_now()
            except Exception as error:
                self.event_bus.publish(
                    "reminder.scheduler_error",
                    error=str(error),
                )
            self._stop.wait(self.poll_seconds)
