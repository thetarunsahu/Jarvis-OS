import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_resume_workspace_without_launch_updates_session(self):
        workspace = self.manager.register_workspace("Demo Project", self.project)
        self.manager.capture_session(
            workspace["workspace_id"],
            state={"next_action": "Continue implementation"},
            summary="Previous session.",
        )

        result = self.manager.resume_workspace("Demo Project", launch=False)

        self.assertTrue(result["ok"])
        self.assertIn("Resumed workspace: Demo Project", result["message"])
        latest = self.store.latest_session(workspace["workspace_id"])
        self.assertEqual(latest["summary"], "Workspace resumed through JARVIS.")
        self.assertEqual(latest["state"]["resume_action"], "planned")

    @patch("workspace.session_manager.subprocess.Popen")
    @patch("workspace.session_manager.ApplicationTools.resolve")
    def test_resume_workspace_launches_preferred_app_with_project_root(
        self,
        resolve,
        popen,
    ):
        resolve.return_value = ["code"]
        workspace = self.manager.register_workspace(
            "Demo Project",
            self.project,
            preferred_app="vscode",
        )
        self.manager.capture_session(workspace["workspace_id"], state={})

        result = self.manager.resume_workspace("Demo Project", launch=True)

        self.assertTrue(result["ok"])
        resolve.assert_called_once_with("vscode")
        launch_command = popen.call_args.args[0]
        self.assertEqual(launch_command[0], "code")
        self.assertEqual(Path(launch_command[1]), self.project.resolve())
        self.assertFalse(popen.call_args.kwargs["shell"])

    @patch("workspace.session_manager.ApplicationTools.resolve", return_value=None)
    def test_resume_workspace_reports_missing_preferred_app(self, resolve):
        workspace = self.manager.register_workspace(
            "Demo Project",
            self.project,
            preferred_app="vscode",
        )
        result = self.manager.resume_workspace(workspace["workspace_id"], launch=True)

        self.assertFalse(result["ok"])
        self.assertIn("not available", result["message"])

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
