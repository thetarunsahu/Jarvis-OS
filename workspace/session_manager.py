import subprocess
from pathlib import Path

from workspace.workspace_store import WorkspaceStore


class SessionManager:
    """Creates and restores lightweight project sessions without replacing the IDE."""

    def __init__(self, store=None):
        self.store = store or WorkspaceStore()

    def register_workspace(self, name, root_path, repo_url=None, preferred_app="vscode"):
        path = Path(root_path).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Workspace path does not exist: {path}")
        return self.store.upsert_workspace(
            name=name,
            root_path=str(path),
            repo_url=repo_url,
            preferred_app=preferred_app,
        )

    def capture_session(self, reference=None, state=None, summary=None):
        workspace = self.store.find_workspace(reference)
        if workspace is None:
            return None

        root = Path(workspace["root_path"])
        captured = {
            "root_path": str(root),
            "exists": root.exists(),
            "git_branch": self._git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
            "git_status": self._git_value(root, ["status", "--short"]),
        }
        if state:
            captured.update(state)

        return self.store.save_session(
            workspace["workspace_id"],
            captured,
            summary=summary,
        )

    def resume_plan(self, reference=None):
        workspace = self.store.find_workspace(reference)
        if workspace is None:
            return None

        session = self.store.latest_session(workspace["workspace_id"])
        return {
            "workspace": workspace,
            "session": session,
            "root_exists": Path(workspace["root_path"]).exists(),
        }

    def mark_resumed(self, reference=None):
        workspace = self.store.find_workspace(reference)
        if workspace is None:
            return None
        return self.store.touch_workspace(workspace["workspace_id"])

    @staticmethod
    def _git_value(root, args):
        if not (root / ".git").exists():
            return None
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=3,
                shell=False,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None
