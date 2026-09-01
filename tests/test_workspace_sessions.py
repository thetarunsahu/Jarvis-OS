import tempfile
import unittest
from pathlib import Path

from workspace.session_manager import SessionManager
from workspace.workspace_store import WorkspaceStore


class WorkspaceSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.project = self.root / "demo-project"
        self.project.mkdir()
        self.store = WorkspaceStore(db_path=self.root / "jarvis.db")
        self.manager = SessionManager(store=self.store)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_register_and_find_workspace(self):
        workspace = self.manager.register_workspace("Demo Project", self.project)
        found = self.store.find_workspace("demo")

        self.assertEqual(found["workspace_id"], workspace["workspace_id"])
        self.assertEqual(Path(found["root_path"]), self.project.resolve())

    def test_capture_and_resume_session(self):
        workspace = self.manager.register_workspace("Demo Project", self.project)
        session = self.manager.capture_session(
            workspace["workspace_id"],
            state={"open_files": ["README.md"], "next_action": "Run tests"},
            summary="Stopped after wiring the UI.",
        )

        plan = self.manager.resume_plan("Demo Project")

        self.assertTrue(plan["root_exists"])
        self.assertEqual(plan["workspace"]["workspace_id"], workspace["workspace_id"])
        self.assertEqual(session["session_id"], plan["session"]["session_id"])
        self.assertEqual(plan["session"]["state"]["open_files"], ["README.md"])
        self.assertEqual(plan["session"]["state"]["next_action"], "Run tests")

    def test_workspace_database_closes_cleanly_on_windows(self):
        workspace = self.manager.register_workspace("Demo Project", self.project)
        self.manager.capture_session(workspace["workspace_id"], state={})

        db_path = self.store.db_path
        replacement = db_path.with_suffix(".moved")
        db_path.replace(replacement)
        replacement.replace(db_path)

        self.assertTrue(db_path.exists())


if __name__ == "__main__":
    unittest.main()
