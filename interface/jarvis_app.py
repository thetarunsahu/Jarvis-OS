import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.jarvis import Jarvis
from interface.dashboard import JarvisHUD
from interface.home import JarvisHome
from workspace.session_manager import SessionManager


class CommandWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, jarvis, command):
        super().__init__()
        self.jarvis = jarvis
        self.command = command

    @Slot()
    def run(self):
        try:
            response = self.jarvis.process(self.command)
            self.finished.emit(str(response))
        except Exception as error:
            self.failed.emit(str(error))


class JarvisEventBridge(QObject):
    """Moves background JARVIS events safely onto the Qt UI thread."""

    reminder_due = Signal(str)
    task_completed = Signal(str)
    task_failed = Signal(str)

    def on_reminder_due(self, event):
        self.reminder_due.emit(str(event.payload.get("text", "Reminder due")))

    def on_task_completed(self, event):
        self.task_completed.emit(str(event.payload.get("task_id", "")))

    def on_task_failed(self, event):
        self.task_failed.emit(str(event.payload.get("task_id", "")))


class JarvisApp(JarvisHome):
    """Primary AI-first JARVIS desktop experience."""

    def __init__(self):
        super().__init__()
        self.jarvis = Jarvis()
        self.sessions = SessionManager()
        self._command_thread = None
        self._command_worker = None
        self._diagnostics_window = None

        self.command_submitted.connect(self.execute_command)
        self.diagnostics_requested.connect(self.open_diagnostics)
        self.workspace_resume_requested.connect(self.resume_latest_workspace)

        self.event_bridge = JarvisEventBridge(self)
        event_bus = self.jarvis.router.brain.orchestrator.event_bus
        event_bus.subscribe("reminder.due", self.event_bridge.on_reminder_due)
        event_bus.subscribe("task.completed", self.event_bridge.on_task_completed)
        event_bus.subscribe("task.failed", self.event_bridge.on_task_failed)

        self.event_bridge.reminder_due.connect(self._show_reminder)
        self.event_bridge.task_completed.connect(self._background_task_completed)
        self.event_bridge.task_failed.connect(self._background_task_failed)

        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self.refresh_runtime_panels)
        self.task_timer.start(1200)

        self._ensure_jarvis_workspace()
        self.refresh_workspace()
        self.refresh_runtime_panels()
        self.refresh_today()

        scheduler = self.jarvis.router.brain.orchestrator.reminder_scheduler
        if scheduler is not None:
            scheduler.check_now()

    def _ensure_jarvis_workspace(self):
        """Register and refresh the current repository as a resumable workspace."""
        project_root = Path(__file__).resolve().parents[1]
        try:
            workspace = self.sessions.register_workspace(
                name="JARVIS OS",
                root_path=str(project_root),
                repo_url="https://github.com/thetarunsahu/Jarvis-OS",
                preferred_app="vscode",
            )
            previous = self.sessions.store.latest_session(workspace["workspace_id"])
            if previous is None:
                self.sessions.capture_session(
                    workspace["workspace_id"],
                    state={"next_action": "Continue JARVIS development"},
                    summary="JARVIS development workspace initialized.",
                )
            else:
                self.sessions.capture_session(
                    workspace["workspace_id"],
                    summary=previous.get("summary") or "JARVIS workspace refreshed.",
                )
        except Exception as error:
            self.append_message("jarvis", f"Workspace continuity could not initialize: {error}")

    def _capture_latest_task_context(self, summary=None):
        """Persist the latest JARVIS task alongside the current project session."""
        workspace = self.sessions.store.latest_workspace()
        if workspace is None:
            return None

        state = {}
        try:
            tasks = self.jarvis.router.brain.list_tasks(limit=1)
        except Exception:
            tasks = []

        if tasks:
            task = tasks[0]
            state["last_task"] = task.raw_input or task.intent
            state["last_task_status"] = task.status.value
            if task.metadata.get("agent"):
                state["last_task_agent"] = task.metadata["agent"]

        previous = self.sessions.store.latest_session(workspace["workspace_id"]) or {}
        effective_summary = summary or previous.get("summary") or "JARVIS workspace context updated."
        return self.sessions.capture_session(
            workspace["workspace_id"],
            state=state,
            summary=effective_summary,
        )

    def refresh_workspace(self):
        plan = self.sessions.resume_plan()
        if not plan:
            self.set_workspace_empty()
            return

        workspace = plan["workspace"]
        session = plan.get("session") or {}
        state = session.get("state") or {}

        details = []
        project_kind = state.get("project_kind")
        branch = state.get("git_branch")
        git_status = state.get("git_status")
        recent_files = state.get("recent_files") or []
        restorable_files = self.sessions._restorable_files(
            Path(workspace["root_path"]), state
        )
        last_task = state.get("last_task")
        last_task_status = state.get("last_task_status")

        if project_kind:
            details.append(f"Project  ·  {project_kind}")
        if branch:
            details.append(f"Branch  ·  {branch}")
        if git_status:
            changed = len([line for line in git_status.splitlines() if line.strip()])
            details.append(f"Working tree  ·  {changed} change(s)")
        else:
            details.append("Working tree  ·  clean / not captured")
        if restorable_files:
            details.append(f"Restore files  ·  {len(restorable_files)} ready")
        if recent_files:
            details.append("Recent  ·  " + ", ".join(recent_files[:3]))
        if last_task:
            task_line = str(last_task)
            if len(task_line) > 58:
                task_line = task_line[:55] + "..."
            suffix = f" ({last_task_status})" if last_task_status else ""
            details.append(f"Last JARVIS task  ·  {task_line}{suffix}")
        if session.get("summary"):
            details.append(session["summary"])

        resumable = bool(plan.get("root_exists"))
        self.set_workspace(
            workspace["name"],
            details,
            resumable=resumable,
            next_action=state.get("next_action"),
        )

        app = str(workspace.get("preferred_app") or "vscode").upper()
        branch_text = branch or "workspace"
        restore_text = (
            f"{len(restorable_files)} captured file(s)"
            if restorable_files
            else "project root"
        )
        next_action = state.get("next_action") or "Continue from the latest saved session."
        self.workspace_next.setText(
            f"Next: {next_action}\n\nResume package: {app} · {restore_text} · {branch_text}"
        )
        if resumable:
            self.session_strip.setText(
                f"SESSION CONTINUITY  •  READY  •  {app}  •  "
                f"{len(restorable_files)} FILE(S)  •  {branch_text}"
            )

    @Slot()
    def resume_latest_workspace(self):
        """Resume the latest workspace directly from the Home surface."""
        self.set_runtime_status("Restoring workspace", "working")
        self.resume_button.setEnabled(False)
        self.continue_action.setEnabled(False)

        try:
            result = self.sessions.resume_workspace()
        except Exception as error:
            result = {"ok": False, "message": f"Workspace resume failed: {error}"}

        self.append_message("jarvis", result.get("message") or "Workspace resume finished.")
        if result.get("ok"):
            plan = result.get("plan") or {}
            session = plan.get("session") or {}
            state = session.get("state") or {}
            restored = self.sessions._restorable_files(
                Path((plan.get("workspace") or {}).get("root_path", ".")), state
            )
            self.greeting.setText("Workspace restored.")
            if restored:
                self.workspace_next.setText(
                    f"Restored {len(restored)} captured file(s). Continue with the saved next action."
                )
            self.set_runtime_status("Workspace ready", "idle")
        else:
            self.set_runtime_status("Resume failed", "idle")

        self.refresh_workspace()

    @Slot(str)
    def execute_command(self, command):
        command = str(command or "").strip()
        if not command:
            return

        if self._command_thread and self._command_thread.isRunning():
            self.append_message(
                "jarvis",
                "I'm still processing the previous request. Long-running work will move to background tasks when the task runtime accepts it.",
            )
            return

        self.set_runtime_status("Thinking", "thinking")

        thread = QThread(self)
        worker = CommandWorker(self.jarvis, command)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._command_finished)
        worker.failed.connect(self._command_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_command_worker)

        self._command_thread = thread
        self._command_worker = worker
        thread.start()

    @Slot(str)
    def _command_finished(self, response):
        self.append_message("jarvis", response)
        self.set_runtime_status("System ready", "idle")
        try:
            self._capture_latest_task_context()
        except Exception:
            pass
        self.refresh_runtime_panels()
        self.refresh_today()
        self.refresh_workspace()

    @Slot(str)
    def _command_failed(self, error):
        self.append_message("jarvis", f"Command failed: {error}")
        self.set_runtime_status("Error", "idle")
        self.refresh_runtime_panels()

    @Slot()
    def _clear_command_worker(self):
        self._command_thread = None
        self._command_worker = None

    @Slot(str)
    def _show_reminder(self, text):
        QApplication.beep()
        self.append_message("jarvis", f"Reminder: {text}")
        self.set_runtime_status("Reminder due", "idle")
        self.refresh_today()

    @Slot(str)
    def _background_task_completed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return

        message = f"Background task {task.task_id[:8]} completed."
        if task.result:
            message += f"\n{task.result}"
        self.append_message("jarvis", message)
        self.set_runtime_status("Task complete", "idle")
        QApplication.beep()
        try:
            self._capture_latest_task_context()
        except Exception:
            pass
        self.refresh_runtime_panels()
        self.refresh_workspace()

    @Slot(str)
    def _background_task_failed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return

        self.append_message(
            "jarvis",
            f"Background task {task.task_id[:8]} failed.\n{task.error or 'Unknown error.'}",
        )
        self.set_runtime_status("Task failed", "idle")
        QApplication.beep()
        try:
            self._capture_latest_task_context()
        except Exception:
            pass
        self.refresh_runtime_panels()
        self.refresh_workspace()

    def refresh_runtime_panels(self):
        self.refresh_tasks()
        self.refresh_approvals()

    def refresh_tasks(self):
        try:
            tasks = self.jarvis.router.brain.list_tasks(limit=8)
        except Exception:
            return

        active = [
            task
            for task in tasks
            if task.status.value not in {"completed", "failed", "cancelled"}
        ]

        if active:
            task_lines = [
                f"● {task.intent}  ·  {task.status.value.replace('_', ' ')}"
                for task in active[:4]
            ]
            agent_lines = [
                f"{task.metadata.get('agent', 'JARVIS')}  ·  {task.intent}"
                for task in active[:4]
            ]
            self.set_runtime_status("Background work active", "working")
        else:
            recent = tasks[:3]
            task_lines = [
                f"✓ {task.intent}  ·  {task.status.value.replace('_', ' ')}"
                for task in recent
            ]
            agent_lines = []

        self.set_tasks(task_lines)
        self.set_agents(agent_lines)

    def refresh_approvals(self):
        try:
            approvals = self.jarvis.router.brain.list_approvals(limit=4)
        except Exception:
            return

        lines = [
            f"! {request['action']}\n  approve {request['approval_id'][:8]} / deny {request['approval_id'][:8]}"
            for request in approvals
        ]
        self.set_approvals(lines)

    def refresh_today(self):
        try:
            brief = self.jarvis.router.brain.daily_brief()
        except Exception:
            return
        self.set_today(brief)

    @Slot()
    def open_diagnostics(self):
        if self._diagnostics_window is None:
            self._diagnostics_window = JarvisHUD()
            self._diagnostics_window.setWindowTitle("JARVIS · Diagnostics")
        else:
            self._diagnostics_window.showFullScreen()
            self._diagnostics_window.raise_()
            self._diagnostics_window.activateWindow()

    def closeEvent(self, event):
        try:
            self.task_timer.stop()
            try:
                self._capture_latest_task_context(
                    summary="JARVIS closed; latest workspace and task context captured."
                )
            except Exception:
                pass
            if self._diagnostics_window is not None:
                self._diagnostics_window.close()
            self.jarvis.router.brain.shutdown()
        finally:
            super().closeEvent(event)


def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    window = JarvisApp()
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
