import tempfile
import unittest
from pathlib import Path

from core.approval_manager import ApprovalManager
from core.policy_engine import PermissionLevel, PolicyEngine
from tools.tool_registry import ToolRegistry, ToolSpec


class DummyProductivityTools:
    def create_goal(self, title, target_date=None):
        return {"title": title}

    def list_goals(self):
        return []

    def create_reminder(self, text, due_at):
        return {"text": text, "due_at": due_at}

    def list_reminders(self):
        return []


class DummyFileIntelligenceTools:
    def index_files(self):
        return {"indexed": 0, "skipped": 0, "roots": [], "fts": False}

    def search_files(self, query, limit=10):
        return {"query": query, "count": 0, "matches": []}

    def file_index_status(self):
        return {"files": 0, "bytes": 0, "roots": [], "fts": False}


class ApprovalWorkflowTests(unittest.TestCase):
    def test_sensitive_action_waits_for_explicit_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            approvals = ApprovalManager(Path(temp_dir) / "jarvis.db")
            registry = ToolRegistry(
                policy_engine=PolicyEngine(auto_approve_up_to=PermissionLevel.SAFE),
                productivity_tools=DummyProductivityTools(),
                file_intelligence_tools=DummyFileIntelligenceTools(),
                approval_manager=approvals,
            )

            executed = []

            def sensitive_action(value):
                executed.append(value)
                return f"executed:{value}"

            registry.register(
                ToolSpec(
                    name="sensitive_action",
                    handler=sensitive_action,
                    description="Test sensitive action.",
                    permission_level=PermissionLevel.SENSITIVE,
                    parameters={
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                    },
                )
            )

            response = registry.execute("sensitive_action", {"value": "safe-after-approval"})
            self.assertIn("Approval required", response)
            self.assertEqual(executed, [])

            pending = registry.list_pending_approvals()
            self.assertEqual(len(pending), 1)
            approval_id = pending[0]["approval_id"]

            result = registry.resolve_approval(approval_id[:8], approved=True)
            self.assertEqual(result, "executed:safe-after-approval")
            self.assertEqual(executed, ["safe-after-approval"])
            self.assertEqual(approvals.get(approval_id)["status"], "executed")

    def test_denied_action_never_executes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            approvals = ApprovalManager(Path(temp_dir) / "jarvis.db")
            registry = ToolRegistry(
                productivity_tools=DummyProductivityTools(),
                file_intelligence_tools=DummyFileIntelligenceTools(),
                approval_manager=approvals,
            )
            executed = []
            registry.register(
                ToolSpec(
                    name="delete_something",
                    handler=lambda: executed.append(True),
                    description="Test delete action.",
                    permission_level=PermissionLevel.SENSITIVE,
                )
            )

            registry.execute("delete_something")
            pending = registry.list_pending_approvals()
            result = registry.resolve_approval(pending[0]["approval_id"][:8], approved=False)

            self.assertIn("Denied approval", result)
            self.assertEqual(executed, [])


if __name__ == "__main__":
    unittest.main()
