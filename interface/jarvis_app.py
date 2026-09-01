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

        root = self.layout()
        insert_at = max(0, root.count() - 2)
        root.insertWidget(insert_at, self.response_panel)
        root.insertWidget(insert_at + 1, self.task_panel)

        self.input.returnPressed.connect(self.execute_command)

        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self.refresh_tasks)
        self.task_timer.start(1200)
        self.refresh_tasks()

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
        self.refresh_tasks()

    @Slot(str)
    def _command_failed(self, error):
        self.response_panel.set_lines([f"Command failed: {error}"])
        self.status.setText("ERROR")
        self.refresh_tasks()

    @Slot()
    def _clear_command_worker(self):
        self._command_thread = None
        self._command_worker = None

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
