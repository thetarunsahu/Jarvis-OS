import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.jarvis import Jarvis
from interface.dashboard import JarvisHUD
from interface.shell import JarvisShell
from voice.voice_manager import VoiceManager
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
            self.finished.emit(str(self.jarvis.process(self.command)))
        except Exception as error:
            self.failed.emit(str(error))


class VoiceListenWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, voice, duration=6):
        super().__init__()
        self.voice = voice
        self.duration = duration

    @Slot()
    def run(self):
        try:
            self.finished.emit(str(self.voice.listen(duration=self.duration)))
        except Exception as error:
            self.failed.emit(str(error))


class SpeechWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, voice, text):
        super().__init__()
        self.voice = voice
        self.text = text

    @Slot()
    def run(self):
        try:
            self.voice.speak(self.text)
            self.finished.emit()
        except Exception as error:
            self.failed.emit(str(error))


class FileIndexWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, file_intelligence):
        super().__init__()
        self.file_intelligence = file_intelligence

    @Slot()
    def run(self):
        try:
            self.file_intelligence.index_files()
            self.finished.emit(self.file_intelligence.file_index_status())
        except Exception as error:
            self.failed.emit(str(error))


class JarvisEventBridge(QObject):
    reminder_due = Signal(str)
    task_completed = Signal(str)
    task_failed = Signal(str)

    def on_reminder_due(self, event):
        self.reminder_due.emit(str(event.payload.get("text", "Reminder due")))

    def on_task_completed(self, event):
        self.task_completed.emit(str(event.payload.get("task_id", "")))

    def on_task_failed(self, event):
        self.task_failed.emit(str(event.payload.get("task_id", "")))


class JarvisApp(JarvisShell):
    """Operational JARVIS desktop app backed by real project/runtime state."""

    def __init__(self):
        super().__init__()
        self.jarvis = Jarvis()
        self.sessions = SessionManager()
        self.voice = VoiceManager()

        self._command_thread = None
        self._command_worker = None
        self._voice_thread = None
        self._voice_worker = None
        self._speech_thread = None
        self._speech_worker = None
        self._index_thread = None
        self._index_worker = None
        self._diagnostics_window = None

        self.command_submitted.connect(self.execute_command)
        self.diagnostics_requested.connect(self.open_diagnostics)
        self.workspace_resume_requested.connect(self.resume_latest_workspace)
        self.file_search_requested.connect(self.search_files_for_ui)
        self.file_reindex_requested.connect(self.reindex_files_for_ui)
        self.listen_button.clicked.connect(self.start_voice_input)

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
        self.refresh_file_status()

        scheduler = self.jarvis.router.brain.orchestrator.reminder_scheduler
        if scheduler is not None:
            scheduler.check_now()

        QTimer.singleShot(450, self._speak_startup_greeting)

    def _speak_startup_greeting(self):
        self.speak_response("JARVIS online. Ready when you are.")

    def _ensure_jarvis_workspace(self):
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
            workspace["workspace_id"], state=state, summary=effective_summary
        )

    def refresh_workspace(self):
        plan = self.sessions.resume_plan()
        if not plan:
            self.set_workspace_empty()
            return

        workspace = plan["workspace"]
        session = plan.get("session") or {}
        state = session.get("state") or {}
        project_kind = state.get("project_kind")
        branch = state.get("git_branch")
        git_status = state.get("git_status")
        recent_files = state.get("recent_files") or []
        restorable_files = self.sessions._restorable_files(Path(workspace["root_path"]), state)
        last_task = state.get("last_task")
        last_task_status = state.get("last_task_status")

        details = [f"Root  ·  {workspace['root_path']}"]
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
            details.append(f"Captured files  ·  {len(restorable_files)} ready")
        if recent_files:
            details.append("Recent files  ·  " + ", ".join(recent_files[:5]))
        if last_task:
            suffix = f" ({last_task_status})" if last_task_status else ""
            details.append(f"Last JARVIS task  ·  {str(last_task)[:80]}{suffix}")
        if session.get("summary"):
            details.append(f"Session  ·  {session['summary']}")

        resumable = bool(plan.get("root_exists"))
        next_action = state.get("next_action") or "Continue from the latest saved session."
        self.set_workspace(
            workspace["name"], details, resumable=resumable, next_action=next_action
        )

        app = str(workspace.get("preferred_app") or "vscode").upper()
        branch_text = branch or "workspace"
        self.session_strip.setText(
            f"SESSION CONTINUITY  •  {'READY' if resumable else 'UNAVAILABLE'}  •  "
            f"{app}  •  {len(restorable_files)} FILE(S)  •  {branch_text}"
        )

    @Slot()
    def resume_latest_workspace(self):
        self.set_runtime_status("Restoring workspace", "working")
        self.resume_button.setEnabled(False)
        self.continue_action.setEnabled(False)
        self.workspace_page_resume.setEnabled(False)

        try:
            result = self.sessions.resume_workspace()
        except Exception as error:
            result = {"ok": False, "message": f"Workspace resume failed: {error}"}

        message = result.get("message") or "Workspace resume finished."
        self.append_message("jarvis", message)
        self.speak_response(message)
        if result.get("ok"):
            self.greeting.setText("Workspace restored.")
            self.set_runtime_status("Workspace ready", "idle")
        else:
            self.set_runtime_status("Resume failed", "idle")
        self.refresh_workspace()

    def refresh_file_status(self):
        try:
            status = self.jarvis.router.file_intelligence.file_index_status()
        except Exception as error:
            self.file_status_label.setText(f"File index unavailable: {error}")
            return
        self.set_file_status(status)

    @Slot(str)
    def search_files_for_ui(self, query):
        query = str(query or "").strip()
        if not query:
            return
        self.file_result_title.setText(f"Searching for “{query}”…")
        try:
            result = self.jarvis.router.file_intelligence.search_files(query=query, limit=20)
        except Exception as error:
            self.file_result_title.setText(f"Search failed: {error}")
            self.file_results.clear()
            return
        self.set_file_results(query, result.get("matches") or [])

    @Slot()
    def reindex_files_for_ui(self):
        if self._index_thread and self._index_thread.isRunning():
            return
        self.set_file_indexing(True)
        self.file_status_label.setText("Refreshing the local file index in the background…")

        thread = QThread(self)
        worker = FileIndexWorker(self.jarvis.router.file_intelligence)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._file_index_finished)
        worker.failed.connect(self._file_index_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_index_worker)
        self._index_thread = thread
        self._index_worker = worker
        thread.start()

    @Slot(dict)
    def _file_index_finished(self, status):
        self.set_file_indexing(False)
        self.set_file_status(status)

    @Slot(str)
    def _file_index_failed(self, error):
        self.set_file_indexing(False)
        self.file_status_label.setText(f"File indexing failed: {error}")

    @Slot()
    def _clear_index_worker(self):
        self._index_thread = None
        self._index_worker = None

    @Slot()
    def start_voice_input(self):
        if self._voice_thread and self._voice_thread.isRunning():
            return
        if self._speech_thread and self._speech_thread.isRunning():
            self.append_message("jarvis", "Let me finish speaking first.")
            return
        if self._command_thread and self._command_thread.isRunning():
            self.append_message("jarvis", "I am still processing the previous request.")
            return

        self.listen_button.setText("Listening…")
        self.listen_button.setEnabled(False)
        self.set_runtime_status("Listening", "working")
        thread = QThread(self)
        worker = VoiceListenWorker(self.voice, duration=6)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._voice_recognized)
        worker.failed.connect(self._voice_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_voice_worker)
        self._voice_thread = thread
        self._voice_worker = worker
        thread.start()

    @Slot(str)
    def _voice_recognized(self, text):
        command = str(text or "").strip()
        self.listen_button.setText("Voice")
        self.listen_button.setEnabled(True)
        if not command:
            message = "I didn't catch that. Try again."
            self.append_message("jarvis", message)
            self.set_runtime_status("System ready", "idle")
            self.speak_response(message)
            return
        self.show_page(self.PAGE_HOME)
        self.append_message("you", command)
        self.set_runtime_status("Understood", "thinking")
        self.execute_command(command)

    @Slot(str)
    def _voice_failed(self, error):
        self.listen_button.setText("Voice")
        self.listen_button.setEnabled(True)
        self.append_message("jarvis", f"Voice input unavailable: {error}")
        self.set_runtime_status("Voice unavailable", "idle")

    @Slot()
    def _clear_voice_worker(self):
        self._voice_thread = None
        self._voice_worker = None

    def speak_response(self, text):
        value = str(text or "").strip()
        if not value or (self._speech_thread and self._speech_thread.isRunning()):
            return
        self.listen_button.setText("Speaking…")
        self.listen_button.setEnabled(False)
        self.set_runtime_status("Speaking", "working")
        thread = QThread(self)
        worker = SpeechWorker(self.voice, value)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._speech_finished)
        worker.failed.connect(self._speech_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_speech_worker)
        self._speech_thread = thread
        self._speech_worker = worker
        thread.start()

    @Slot()
    def _speech_finished(self):
        self.listen_button.setText("Voice")
        self.listen_button.setEnabled(True)
        self.set_runtime_status("System ready", "idle")

    @Slot(str)
    def _speech_failed(self, error):
        self.listen_button.setText("Voice")
        self.listen_button.setEnabled(True)
        self.set_runtime_status("System ready", "idle")
        self.append_message("jarvis", f"Speech output unavailable: {error}")

    @Slot()
    def _clear_speech_worker(self):
        self._speech_thread = None
        self._speech_worker = None

    @Slot(str)
    def execute_command(self, command):
        command = str(command or "").strip()
        if not command:
            return
        if self._command_thread and self._command_thread.isRunning():
            self.append_message("jarvis", "I am still processing the previous request.")
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
        try:
            self._capture_latest_task_context()
        except Exception:
            pass
        self.refresh_runtime_panels()
        self.refresh_today()
        self.refresh_workspace()
        self.speak_response(response)

    @Slot(str)
    def _command_failed(self, error):
        message = f"Command failed: {error}"
        self.append_message("jarvis", message)
        self.set_runtime_status("Error", "idle")
        self.refresh_runtime_panels()
        self.speak_response(message)

    @Slot()
    def _clear_command_worker(self):
        self._command_thread = None
        self._command_worker = None

    @Slot(str)
    def _show_reminder(self, text):
        QApplication.beep()
        message = f"Reminder: {text}"
        self.append_message("jarvis", message)
        self.refresh_today()
        self.speak_response(message)

    @Slot(str)
    def _background_task_completed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return
        message = f"Background task {task.task_id[:8]} completed."
        if task.result:
            message += f"\n{task.result}"
        self.append_message("jarvis", message)
        QApplication.beep()
        self.refresh_runtime_panels()
        self.refresh_workspace()
        self.speak_response(message)

    @Slot(str)
    def _background_task_failed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return
        message = f"Background task {task.task_id[:8]} failed.\n{task.error or 'Unknown error.'}"
        self.append_message("jarvis", message)
        QApplication.beep()
        self.refresh_runtime_panels()
        self.refresh_workspace()
        self.speak_response(message)

    def refresh_runtime_panels(self):
        self.refresh_tasks()
        self.refresh_approvals()

    def refresh_tasks(self):
        try:
            tasks = self.jarvis.router.brain.list_tasks(limit=10)
        except Exception:
            return

        active = [
            task for task in tasks
            if task.status.value not in {"completed", "failed", "cancelled"}
        ]
        display_tasks = active[:6] if active else tasks[:6]
        task_lines = []
        for task in display_tasks:
            symbol = "●" if task in active else ("✓" if task.status.value == "completed" else "!")
            label = task.raw_input or task.intent
            if len(label) > 72:
                label = label[:69] + "..."
            task_lines.append(
                f"{symbol} {label}\n   {task.status.value.replace('_', ' ')} · {task.intent}"
            )

        agent_lines = [
            f"● {task.metadata.get('agent', 'JARVIS')} · {task.intent}"
            for task in active[:5]
        ]
        self.set_tasks(task_lines)
        self.set_agents(agent_lines)
        if active and not (self._speech_thread and self._speech_thread.isRunning()):
            self.set_runtime_status("Background work active", "working")

    def refresh_approvals(self):
        try:
            approvals = self.jarvis.router.brain.list_approvals(limit=6)
        except Exception:
            return
        lines = [
            f"! {request['action']}\n  {request['approval_id'][:8]} · {request['permission_level']}"
            for request in approvals
        ]
        self.set_approvals(lines)

    def refresh_today(self):
        try:
            self.set_today(self.jarvis.router.brain.daily_brief())
        except Exception:
            pass

    @Slot()
    def open_diagnostics(self):
        if self._diagnostics_window is None:
            self._diagnostics_window = JarvisHUD()
            self._diagnostics_window.setWindowTitle("JARVIS · Diagnostics")
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

            for thread in (
                self._voice_thread,
                self._speech_thread,
                self._command_thread,
                self._index_thread,
            ):
                if thread is not None and thread.isRunning():
                    thread.quit()
                    thread.wait(7000)
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
