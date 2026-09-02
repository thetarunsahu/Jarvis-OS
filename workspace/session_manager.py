import os
import subprocess
from pathlib import Path

from tools.application_tools import ApplicationTools
from workspace.workspace_store import WorkspaceStore


IGNORED_CONTEXT_DIRS = {
    ".git",
    ".idea",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".next",
}


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
        previous = self.store.latest_session(workspace["workspace_id"]) or {}
        previous_state = dict(previous.get("state") or {})

        # Preserve useful continuity fields from the previous snapshot, then
        # refresh deterministic project facts. This prevents a shutdown or
        # resume snapshot from accidentally erasing next_action/open_files.
        captured = previous_state
        captured.update(
            {
                "root_path": str(root),
                "exists": root.exists(),
                "git_branch": self._git_value(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
                "git_status": self._git_value(root, ["status", "--short"]),
                "project_kind": self._project_kind(root),
                "recent_files": self._recent_files(root),
            }
        )
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
        """Restore deterministic project context and optionally launch its IDE."""
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

        session = plan.get("session") or {}
        session_state = session.get("state") or {}
        launch_result = None
        if launch:
            launch_result = self._launch_workspace(workspace, session_state)
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
        if state.get("project_kind"):
            lines.append(f"Project: {state['project_kind']}")
        if state.get("git_branch"):
            lines.append(f"Git branch: {state['git_branch']}")
        git_status = state.get("git_status")
        if git_status:
            changed = len([line for line in git_status.splitlines() if line.strip()])
            lines.append(f"Working tree changes: {changed}")
        if state.get("next_action"):
            lines.append(f"Next action: {state['next_action']}")
        open_files = self._restorable_files(Path(workspace["root_path"]), state)
        if open_files:
            lines.append("Restore files: " + ", ".join(open_files[:5]))
        recent_files = state.get("recent_files") or []
        if recent_files:
            lines.append("Recent files: " + ", ".join(recent_files[:5]))
        if state.get("last_task"):
            lines.append(f"Last JARVIS task: {state['last_task']}")
        if session.get("summary"):
            lines.append(f"Last session: {session['summary']}")
        return "\n".join(lines)

    def mark_resumed(self, reference=None):
        workspace = self.store.find_workspace(reference)
        if workspace is None:
            return None
        return self.store.touch_workspace(workspace["workspace_id"])

    @staticmethod
    def _project_kind(root):
        if not root.exists() or not root.is_dir():
            return None

        signals = [
            ("pyproject.toml", "Python"),
            ("requirements.txt", "Python"),
            ("package.json", "Node / JavaScript"),
            ("Cargo.toml", "Rust"),
            ("go.mod", "Go"),
        ]
        for filename, kind in signals:
            if (root / filename).exists():
                return kind

        if any(root.glob("*.sln")) or any(root.glob("*.csproj")):
            return ".NET"
        return "General project"

    @staticmethod
    def _recent_files(root, limit=6, scan_limit=5000):
        if not root.exists() or not root.is_dir():
            return []

        candidates = []
        scanned = 0
        try:
            for current, dirs, files in os.walk(root):
                dirs[:] = [name for name in dirs if name not in IGNORED_CONTEXT_DIRS]
                for filename in files:
                    scanned += 1
                    if scanned > scan_limit:
                        break
                    path = Path(current) / filename
                    try:
                        stat = path.stat()
                    except OSError:
                        continue
                    if stat.st_size > 5 * 1024 * 1024:
                        continue
                    candidates.append((stat.st_mtime, path))
                if scanned > scan_limit:
                    break
        except OSError:
            return []

        candidates.sort(key=lambda item: item[0], reverse=True)
        result = []
        for _, path in candidates[: max(1, int(limit))]:
            try:
                result.append(str(path.relative_to(root)))
            except ValueError:
                result.append(str(path))
        return result

    @staticmethod
    def _restorable_files(root, state, limit=8):
        """Return captured files that still exist inside the workspace root."""
        result = []
        try:
            resolved_root = root.resolve()
        except OSError:
            return result

        for item in (state or {}).get("open_files") or []:
            if len(result) >= max(1, int(limit)):
                break
            candidate = Path(item)
            if not candidate.is_absolute():
                candidate = resolved_root / candidate
            try:
                resolved = candidate.resolve()
                resolved.relative_to(resolved_root)
            except (OSError, ValueError):
                continue
            if resolved.exists() and resolved.is_file():
                result.append(str(resolved))
        return result

    @classmethod
    def _launch_workspace(cls, workspace, session_state=None):
        app = str(workspace.get("preferred_app") or "vscode").strip().lower()
        root_path = Path(workspace["root_path"]).resolve()
        root = str(root_path)
        command = ApplicationTools.resolve(app)

        if command is None:
            return {
                "ok": False,
                "message": f"Preferred application '{app}' is not available.",
            }

        launch_command = [*command, root]
        restored_files = []
        if app == "vscode":
            restored_files = cls._restorable_files(root_path, session_state or {})
            launch_command.extend(restored_files)

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

        message = f"Opened {workspace['name']} in {app}."
        if restored_files:
            message += f" Restored {len(restored_files)} captured file(s)."
        return {
            "ok": True,
            "message": message,
            "restored_files": restored_files,
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
