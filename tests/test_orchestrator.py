import tempfile
import unittest
from pathlib import Path

from core.event_bus import EventBus
from core.intent_engine import IntentEngine
from core.orchestrator import Orchestrator
from core.task import TaskStatus
from tasks.background_runtime import BackgroundTaskRuntime
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore


class FakeModelRouter:
    def generate(self, task, context=None, tools=None, executor=None):
        return f"done:{task.intent}"


class FakeTools:
    def get_tool_definitions(self):
        return []

    def execute(self, tool_name, arguments=None, approved=False):
        return None


class OrchestratorTests(unittest.TestCase):
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
        self.orchestrator = Orchestrator(
            intent_engine=IntentEngine(),
            model_router=FakeModelRouter(),
            tool_registry=FakeTools(),
            event_bus=self.events,
            task_store=self.store,
            task_manager=self.manager,
            runtime=self.runtime,
        )

    def tearDown(self):
        self.runtime.shutdown(wait=True)
        self.temp_dir.cleanup()

    def test_foreground_task_completes_synchronously(self):
        result = self.orchestrator.handle("hello jarvis")
        self.assertEqual(result, "done:conversation")

        task = self.store.list(limit=1)[0]
        self.assertEqual(task.status, TaskStatus.COMPLETED)

    def test_background_task_returns_immediately_and_finishes(self):
        response = self.orchestrator.handle("deep research about ai agents")
        self.assertIn("Started background task", response)

        task = self.store.list(limit=1)[0]
        future = self.runtime.future(task.task_id)
        self.assertIsNotNone(future)
        self.assertEqual(future.result(timeout=2), "done:research")

        persisted = self.store.get(task.task_id)
        self.assertEqual(persisted.status, TaskStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
