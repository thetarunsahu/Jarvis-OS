import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.jarvis import Jarvis
from interface.dashboard import InfoPanel, JarvisHUD


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


class JarvisApp(JarvisHUD):
    """Functional desktop shell wired to the JARVIS core.

    Long model calls run off the Qt UI thread so the HUD stays responsive.
    JARVIS background tasks continue independently through TaskRuntime.
    """

    def __init__(self):
        super().__init__()
        self.jarvis = Jarvis()
        self._command_thread = None
        self._command_worker = None

        self.response_panel = InfoPanel(
            "JARVIS RESPONSE",
            ["Ready. Ask JARVIS anything."],
        )
        self.response_panel.info.setWordWrap(True)
        self.response_panel.setMaximumHeight(125)

        self.task_panel = InfoPanel(
            "ACTIVE TASKS",
            ["No active tasks."],
        )
        self.task_panel.info.setWordWrap(True)
        self.task_panel.setMaximumHeight(120)

        self.approval_panel = InfoPanel(
            "APPROVALS",
            ["No pending approvals."],
        )
        self.approval_panel.info.setWordWrap(True)
        self.approval_panel.setMaximumHeight(105)

        root = self.layout()
        insert_at = max(0, root.count() - 2)
        root.insertWidget(insert_at, self.response_panel)
        root.insertWidget(insert_at + 1, self.task_panel)
        root.insertWidget(insert_at + 2, self.approval_panel)

        self.input.returnPressed.connect(self.execute_command)

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

        scheduler = self.jarvis.router.brain.orchestrator.reminder_scheduler
        if scheduler is not None:
            scheduler.check_now()

    def execute_command(self):
        command = self.input.text().strip()
        if not command:
            return

        if self._command_thread and self._command_thread.isRunning():
            self.status.setText("JARVIS IS PROCESSING")
            return

        self.input.clear()
        self.status.setText("PROCESSING")
        self.response_panel.set_lines([f"> {command}", "Working..."])

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
        self.response_panel.set_lines([response])
        self.status.setText("SYSTEM READY")
        self.refresh_runtime_panels()

    @Slot(str)
    def _command_failed(self, error):
        self.response_panel.set_lines([f"Command failed: {error}"])
        self.status.setText("ERROR")
        self.refresh_runtime_panels()

    @Slot()
    def _clear_command_worker(self):
        self._command_thread = None
        self._command_worker = None

    @Slot(str)
    def _show_reminder(self, text):
        QApplication.beep()
        self.response_panel.set_lines(["REMINDER", text])
        self.status.setText("REMINDER DUE")

    @Slot(str)
    def _background_task_completed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return

        message = f"Background task {task.task_id[:8]} completed."
        if task.result:
            message += f"\n{task.result}"
        self.response_panel.set_lines([message])
        self.status.setText("TASK COMPLETE")
        QApplication.beep()
        self.refresh_runtime_panels()

    @Slot(str)
    def _background_task_failed(self, task_id):
        task = self.jarvis.router.brain.get_task(task_id)
        if task is None or not task.background:
            return

        self.response_panel.set_lines(
            [
                f"Background task {task.task_id[:8]} failed.",
                task.error or "Unknown error.",
            ]
        )
        self.status.setText("TASK FAILED")
        QApplication.beep()
        self.refresh_runtime_panels()

    def refresh_runtime_panels(self):
        self.refresh_tasks()
        self.refresh_approvals()

    def refresh_tasks(self):
        try:
            tasks = self.jarvis.router.brain.list_tasks(limit=5)
        except Exception:
            return

        active = [
            task
            for task in tasks
            if task.status.value
            not in {"completed", "failed", "cancelled"}
        ]

        if active:
            lines = [
                f"● {task.task_id[:8]}  {task.status.value.upper()}  {task.intent}"
                for task in active[:4]
            ]
        else:
            recent = tasks[:3]
            if recent:
                lines = [
                    f"✓ {task.task_id[:8]}  {task.status.value.upper()}  {task.intent}"
                    for task in recent
                ]
            else:
                lines = ["No tasks recorded yet."]

        self.task_panel.set_lines(lines)

    def refresh_approvals(self):
        try:
            approvals = self.jarvis.router.brain.list_approvals(limit=4)
        except Exception:
            return

        if approvals:
            lines = [
                f"! {request['approval_id'][:8]}  {request['action']}  "
                f"→ approve {request['approval_id'][:8]} / deny {request['approval_id'][:8]}"
                for request in approvals
            ]
        else:
            lines = ["No pending approvals."]

        self.approval_panel.set_lines(lines)

    def closeEvent(self, event):
        try:
            self.task_timer.stop()
            self.jarvis.router.brain.shutdown()
        finally:
            super().closeEvent(event)


def run_app():
    app = QApplication.instance() or QApplication(sys.argv)
    window = JarvisApp()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
