import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.task import Task, TaskStatus
from productivity.accountability_engine import AccountabilityEngine
from productivity.productivity_store import ProductivityStore
from tasks.task_store import TaskStore


class AccountabilityEngineTests(unittest.TestCase):
    def test_snapshot_surfaces_overdue_due_today_and_task_health(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            productivity = ProductivityStore(db_path=db_path)
            tasks = TaskStore(db_path=db_path)

            tz = timezone(timedelta(hours=5, minutes=30))
            now = datetime(2026, 9, 2, 10, 0, tzinfo=tz)

            goal = productivity.create_goal(
                "Finish backend milestone",
                target_date=(now + timedelta(days=3)).isoformat(),
            )
            productivity.update_goal(goal["goal_id"], progress=40)

            productivity.create_reminder(
                "Overdue DSA block",
                (now - timedelta(hours=1)).isoformat(),
            )
            productivity.create_reminder(
                "Backend practice",
                (now + timedelta(hours=2)).isoformat(),
            )

            completed = Task(raw_input="completed task")
            completed.set_status(TaskStatus.RUNNING)
            completed.complete("done")
            tasks.save(completed)

            failed = Task(raw_input="failed task")
            failed.fail("boom")
            tasks.save(failed)

            engine = AccountabilityEngine(
                productivity_store=productivity,
                task_store=tasks,
            )
            snapshot = engine.snapshot(now=now)

            self.assertEqual(len(snapshot["overdue_reminders"]), 1)
            self.assertEqual(len(snapshot["due_today"]), 1)
            self.assertEqual(len(snapshot["goals_at_risk"]), 1)
            self.assertEqual(snapshot["recent_task_counts"]["completed"], 1)
            self.assertEqual(snapshot["recent_task_counts"]["failed"], 1)

            brief = engine.render_brief(now=now)
            self.assertIn("Overdue DSA block", brief)
            self.assertIn("Backend practice", brief)
            self.assertIn("Finish backend milestone", brief)


if __name__ == "__main__":
    unittest.main()
