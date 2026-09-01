import subprocess
from pathlib import Path

from tools.application_tools import ApplicationTools
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

    def resume_workspace(self, reference=None, launch=True):
        """Restore the latest workspace context and optionally launch its IDE.

        This intentionally restores only deterministic, safe state today: the
        project root, preferred application and recorded session metadata. Open
        editor tabs, browser tabs and terminals remain future adapters instead
        of being faked as already restored.
        """
        plan = self.resume_plan(reference)
        if plan is None:
            return {
                "ok": False,
                "message": "No matching workspace is registered.",
                "plan": None,
            }

        workspace = plan["workspace"]
        root = Path(workspace["root_path"])
        if not root.exists() or not root.is_dir():
            return {
                "ok": False,
                "message": f"Workspace path is unavailable: {root}",
                "plan": plan,
            }

        launch_result = None
        if launch:
            launch_result = self._launch_workspace(workspace)
            if not launch_result["ok"]:
                return {
                    "ok": False,
                    "message": launch_result["message"],
                    "plan": plan,
                }

        self.mark_resumed(workspace["workspace_id"])
        latest = self.capture_session(
            workspace["workspace_id"],
            state={"resume_action": "launched" if launch else "planned"},
            summary="Workspace resumed through JARVIS.",
        )
        plan["session"] = latest

        message = f"Resumed workspace: {workspace['name']}"
        if launch_result:
            message += f"\n{launch_result['message']}"
        return {
            "ok": True,
            "message": message,
            "plan": plan,
        }

    def describe_resume(self, reference=None):
        plan = self.resume_plan(reference)
        if plan is None:
            return "No matching workspace is registered."

        workspace = plan["workspace"]
        session = plan.get("session") or {}
        state = session.get("state") or {}
        lines = [
            f"Workspace: {workspace['name']}",
            f"Root: {workspace['root_path']}",
            f"Preferred app: {workspace.get('preferred_app') or 'not set'}",
        ]
        if state.get("git_branch"):
            lines.append(f"Git branch: {state['git_branch']}")
        git_status = state.get("git_status")
        if git_status:
            changed = len([line for line in git_status.splitlines() if line.strip()])
            lines.append(f"Working tree changes: {changed}")
        if session.get("summary"):
            lines.append(f"Last session: {session['summary']}")
        return "\n".join(lines)

    def mark_resumed(self, reference=None):
        workspace = self.store.find_workspace(reference)
        if workspace is None:
            return None
        return self.store.touch_workspace(workspace["workspace_id"])

    @staticmethod
    def _launch_workspace(workspace):
        app = str(workspace.get("preferred_app") or "vscode").strip().lower()
        root = str(Path(workspace["root_path"]).resolve())
        command = ApplicationTools.resolve(app)

        if command is None:
            return {
                "ok": False,
                "message": f"Preferred application '{app}' is not available.",
            }

        launch_command = [*command, root]
        try:
            subprocess.Popen(
                launch_command,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as error:
            return {
                "ok": False,
                "message": f"Could not launch {app}: {error}",
            }

        return {
            "ok": True,
            "message": f"Opened {workspace['name']} in {app}.",
        }

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
