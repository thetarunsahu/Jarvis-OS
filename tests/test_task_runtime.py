import tempfile
import unittest
from pathlib import Path

from core.event_bus import EventBus
from core.task import Task, TaskStatus
from tasks.background_runtime import BackgroundTaskRuntime
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore


class TaskRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "jarvis-test.db"
        self.store = TaskStore(db_path=db_path)
        self.events = EventBus()
        self.manager = TaskManager(store=self.store, event_bus=self.events)
        self.runtime = BackgroundTaskRuntime(
            task_manager=self.manager,
            max_workers=1,
        )

    def tearDown(self):
        self.runtime.shutdown(wait=True)
        self.temp_dir.cleanup()

    def test_task_lifecycle_is_persisted(self):
        task = Task(raw_input="hello")
        self.manager.register(task)
        self.manager.transition(task, TaskStatus.RUNNING)
        self.manager.complete(task, result="world")

        persisted = self.store.get(task.task_id)
        self.assertEqual(persisted.status, TaskStatus.COMPLETED)
        self.assertEqual(persisted.result, "world")

    def test_background_runtime_completes_task(self):
        task = Task(
            raw_input="research agents",
            intent="research",
            background=True,
        )
        self.manager.register(task)

        future = self.runtime.submit(task, lambda current: "finished")
        self.assertEqual(future.result(timeout=2), "finished")

        persisted = self.store.get(task.task_id)
        self.assertEqual(persisted.status, TaskStatus.COMPLETED)
        self.assertEqual(persisted.result, "finished")


if __name__ == "__main__":
    unittest.main()
