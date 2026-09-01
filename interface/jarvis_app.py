import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.jarvis import Jarvis
from interface.dashboard import JarvisHUD
from interface.home import JarvisHome


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
    """Primary AI-first JARVIS desktop experience.

    The old telemetry-heavy HUD remains available as a Diagnostics view, while
    Home is now centered around conversation, current work, agent activity,
    tasks and approvals.
    """

    def __init__(self):
        super().__init__()
        self.jarvis = Jarvis()
        self._command_thread = None
        self._command_worker = None
        self._diagnostics_window = None

        self.command_submitted.connect(self.execute_command)
        self.diagnostics_requested.connect(self.open_diagnostics)

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
        self.refresh_runtime_panels()
        self.refresh_today()

        scheduler = self.jarvis.router.brain.orchestrator.reminder_scheduler
        if scheduler is not None:
            scheduler.check_now()

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
        self.refresh_runtime_panels()
        self.refresh_today()

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
        self.refresh_runtime_panels()

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
        self.refresh_runtime_panels()

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
