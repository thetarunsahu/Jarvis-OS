import tempfile
import unittest
from pathlib import Path

from core.approval_manager import ApprovalManager
from core.event_bus import EventBus
from core.orchestrator import Orchestrator
from core.policy_engine import PermissionLevel
from core.task import TaskStatus
from files.file_index import FileIndex
from productivity.accountability_engine import AccountabilityEngine
from productivity.productivity_store import ProductivityStore
from tasks.background_runtime import BackgroundTaskRuntime
from tasks.task_manager import TaskManager
from tasks.task_store import TaskStore
from tools.file_intelligence_tools import FileIntelligenceTools
from tools.productivity_tools import ProductivityTools
from tools.tool_registry import ToolRegistry, ToolSpec


class SensitiveToolModelRouter:
    def generate(self, task, context=None, tools=None, executor=None):
        return executor("sensitive_action", {"value": "approved-value"})


class ApprovalTaskLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        db_path = root / "jarvis.db"

        self.task_store = TaskStore(db_path=db_path)
        self.events = EventBus()
        self.task_manager = TaskManager(
            store=self.task_store,
            event_bus=self.events,
        )
        self.runtime = BackgroundTaskRuntime(
            task_manager=self.task_manager,
            max_workers=1,
        )

        productivity_store = ProductivityStore(db_path=db_path)
        productivity_tools = ProductivityTools(
            store=productivity_store,
            accountability_engine=AccountabilityEngine(
                productivity_store=productivity_store,
                task_store=self.task_store,
            ),
        )
        file_tools = FileIntelligenceTools(
            index=FileIndex(db_path=db_path, roots=[root])
        )
        approvals = ApprovalManager(db_path=db_path)

        self.registry = ToolRegistry(
            productivity_tools=productivity_tools,
            file_intelligence_tools=file_tools,
            approval_manager=approvals,
        )
        self.executed = []
        self.registry.register(
            ToolSpec(
                name="sensitive_action",
                handler=self._sensitive_action,
                description="Sensitive test action.",
                permission_level=PermissionLevel.SENSITIVE,
                parameters={
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            )
        )

        self.orchestrator = Orchestrator(
            model_router=SensitiveToolModelRouter(),
            tool_registry=self.registry,
            event_bus=self.events,
            task_store=self.task_store,
            task_manager=self.task_manager,
            runtime=self.runtime,
        )

    def tearDown(self):
        self.orchestrator.shutdown()
        self.runtime.shutdown(wait=True)
        self.temp_dir.cleanup()

    def _sensitive_action(self, value):
        self.executed.append(value)
        return f"executed:{value}"

    def test_task_waits_then_completes_after_approval(self):
        response = self.orchestrator.handle("do the sensitive action")
        self.assertIn("Approval required", response)
        self.assertEqual(self.executed, [])

        task = self.task_store.list(limit=1)[0]
        self.assertEqual(task.status, TaskStatus.WAITING_APPROVAL)

        pending = self.registry.list_pending_approvals()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["task_id"], task.task_id)

        result = self.orchestrator.resolve_approval(
            pending[0]["approval_id"][:8],
            approved=True,
        )
        self.assertIn("executed:approved-value", result)
        self.assertEqual(self.executed, ["approved-value"])

        persisted = self.task_store.get(task.task_id)
        self.assertEqual(persisted.status, TaskStatus.COMPLETED)

    def test_denial_cancels_waiting_task(self):
        self.orchestrator.handle("do the sensitive action")
        task = self.task_store.list(limit=1)[0]
        pending = self.registry.list_pending_approvals()

        result = self.orchestrator.resolve_approval(
            pending[0]["approval_id"][:8],
            approved=False,
        )
        self.assertIn("cancelled", result.lower())
        self.assertEqual(self.executed, [])

        persisted = self.task_store.get(task.task_id)
        self.assertEqual(persisted.status, TaskStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
