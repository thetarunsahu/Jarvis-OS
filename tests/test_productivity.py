import tempfile
import unittest
from pathlib import Path

from core.event_bus import EventBus
from productivity.productivity_store import ProductivityStore
from productivity.reminder_scheduler import ReminderScheduler


class ProductivityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "jarvis-test.db"
        self.store = ProductivityStore(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_goal_is_persisted(self):
        goal = self.store.create_goal("Become internship ready")
        self.assertEqual(goal["status"], "active")
        self.assertEqual(goal["progress"], 0)
        self.assertEqual(
            self.store.list_goals()[0]["title"],
            "Become internship ready",
        )

    def test_reminder_time_is_normalized_to_utc(self):
        reminder = self.store.create_reminder(
            "Do DSA",
            "2030-01-01T20:00:00+05:30",
        )
        self.assertEqual(
            reminder["due_at"],
            "2030-01-01T14:30:00+00:00",
        )

    def test_scheduler_emits_due_reminder_once(self):
        reminder = self.store.create_reminder(
            "Review roadmap",
            "2020-01-01T00:00:00+00:00",
        )
        events = []
        bus = EventBus()
        bus.subscribe("reminder.due", lambda event: events.append(event))
        scheduler = ReminderScheduler(
            store=self.store,
            event_bus=bus,
            poll_seconds=60,
        )

        due = scheduler.check_now()
        self.assertEqual(len(due), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["text"], "Review roadmap")
        self.assertEqual(
            self.store.get_reminder(reminder["reminder_id"])["status"],
            "notified",
        )
        self.assertEqual(scheduler.check_now(), [])


if __name__ == "__main__":
    unittest.main()
