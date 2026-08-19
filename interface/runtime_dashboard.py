from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QFrame, QVBoxLayout

from core.jarvis import Jarvis
from interface.dashboard import CYAN, CYAN_DARK, MUTED, PANEL, WHITE, JarvisHUD


@dataclass
class PermissionPrompt:
    request: Any
    done: threading.Event
    allowed: bool = False


class PermissionBridge(QObject):
    """Safely moves permission prompts from a worker thread to the GUI thread."""

    permission_requested = Signal(object)

    def approve(self, request) -> bool:
        prompt = PermissionPrompt(request=request, done=threading.Event())
        self.permission_requested.emit(prompt)
        if not prompt.done.wait(timeout=300):
            return False
        return prompt.allowed


class CoreEventBridge(QObject):
    """Forwards core events to Qt signals without touching widgets off-thread."""

    event_received = Signal(str, object)

    def forward(self, event) -> None:
        self.event_received.emit(event.name, event.payload)


class RequestWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, jarvis: Jarvis, command: str) -> None:
        super().__init__()
        self.jarvis = jarvis
        self.command = command

    @Slot()
    def run(self) -> None:
        try:
            response = self.jarvis.process(self.command)
            self.finished.emit(response)
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class JarvisRuntimeHUD(JarvisHUD):
    """Existing HUD wired to the real JARVIS core through background workers."""

    def __init__(self) -> None:
        super().__init__()

        self.jarvis = Jarvis()
        self.request_thread: QThread | None = None
        self.request_worker: RequestWorker | None = None

        self.permission_bridge = PermissionBridge(self)
        self.permission_bridge.permission_requested.connect(
            self._show_permission_dialog
        )
        self.jarvis.set_permission_approver(self.permission_bridge.approve)

        self.event_bridge = CoreEventBridge(self)
        self.event_bridge.event_received.connect(self._handle_core_event)
        self.jarvis.subscribe("*", self.event_bridge.forward)

        self._install_runtime_panel()
        self._wire_controls()
        self._set_status("READY")

    def _install_runtime_panel(self) -> None:
        panel = QFrame(self)
        panel.setStyleSheet(
            f"""
            QFrame {{
                background: {PANEL};
                border: 1px solid {CYAN_DARK};
                border-radius: 10px;
            }}
            """
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.runtime_label = QLabel("JARVIS RUNTIME")
        self.runtime_label.setStyleSheet(
            f"color: {CYAN}; font-size: 10px; font-weight: bold; letter-spacing: 2px;"
        )

        self.activity_label = QLabel("READY")
        self.activity_label.setStyleSheet(
            f"color: {MUTED}; font-size: 10px; letter-spacing: 1px;"
        )

        self.response_label = QLabel("JARVIS is connected to the local runtime.")
        self.response_label.setWordWrap(True)
        self.response_label.setTextInteractionFlags(
            self.response_label.textInteractionFlags()
        )
        self.response_label.setStyleSheet(
            f"color: {WHITE}; font-size: 12px;"
        )

        layout.addWidget(self.runtime_label)
        layout.addWidget(self.activity_label)
        layout.addWidget(self.response_label)

        root = self.layout()
        insert_at = max(0, root.count() - 2)
        root.insertWidget(insert_at, panel)

    def _wire_controls(self) -> None:
        self.execute_button = None
        self.listen_button = None

        for button in self.findChildren(QPushButton):
            text = button.text().strip().upper()
            if text == "EXECUTE":
                self.execute_button = button
            elif "LISTEN" in text:
                self.listen_button = button

        if self.execute_button is None:
            raise RuntimeError("HUD execute button was not found.")

        try:
            self.execute_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass

        self.execute_button.clicked.connect(self.execute_command)
        self.input.returnPressed.connect(self.execute_command)

        if self.listen_button is not None:
            try:
                self.listen_button.clicked.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.listen_button.clicked.connect(self._voice_not_connected)

    @Slot()
    def execute_command(self) -> None:
        command = self.input.text().strip()
        if not command or self.request_thread is not None:
            return

        self.input.clear()
        self.response_label.setText(f"YOU: {command}")
        self.activity_label.setText("REQUEST ACCEPTED")
        self._set_busy(True)

        thread = QThread(self)
        worker = RequestWorker(self.jarvis, command)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_request_finished)
        worker.failed.connect(self._on_request_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._release_worker)

        self.request_thread = thread
        self.request_worker = worker
        thread.start()

    @Slot(str)
    def _on_request_finished(self, response: str) -> None:
        if response:
            self.response_label.setText(f"JARVIS: {response}")
        self._set_busy(False)

    @Slot(str)
    def _on_request_failed(self, message: str) -> None:
        self.response_label.setText(f"JARVIS ERROR: {message}")
        self._set_status("ERROR")
        self._set_busy(False)

    @Slot()
    def _release_worker(self) -> None:
        self.request_thread = None
        self.request_worker = None

    @Slot(object)
    def _show_permission_dialog(self, prompt: PermissionPrompt) -> None:
        request = prompt.request
        args = request.arguments or {}

        details = "\n".join(
            f"{key}: {value}" for key, value in args.items()
        ) or "No arguments"

        answer = QMessageBox.question(
            self,
            "JARVIS Permission Request",
            (
                f"JARVIS wants to run: {request.tool_name}\n\n"
                f"Risk: {request.level.value}\n"
                f"Reason: {request.reason}\n\n"
                f"Arguments:\n{details}\n\n"
                "Allow this action?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        prompt.allowed = answer == QMessageBox.Yes
        prompt.done.set()

    @Slot(str, object)
    def _handle_core_event(self, event_name: str, payload: dict[str, Any]) -> None:
        if event_name == "state_changed":
            self._set_status(str(payload.get("current", "READY")))
            return

        if event_name == "tool_started":
            tool = payload.get("tool_name") or payload.get("tool") or "tool"
            self.activity_label.setText(f"EXECUTING // {tool}")
            return

        if event_name == "tool_finished":
            tool = payload.get("tool_name") or payload.get("tool") or "tool"
            self.activity_label.setText(f"VERIFYING // {tool}")
            return

        if event_name == "permission_required":
            tool = payload.get("tool_name", "tool")
            self.activity_label.setText(f"PERMISSION REQUIRED // {tool}")
            return

        if event_name == "permission_denied":
            tool = payload.get("tool_name", "tool")
            self.activity_label.setText(f"DENIED // {tool}")
            return

        if event_name == "error":
            message = payload.get("message", "Unknown core error")
            self.response_label.setText(f"JARVIS ERROR: {message}")

    def _set_status(self, state: str) -> None:
        state = state.upper()
        self.status.setText(state)

        if hasattr(self, "activity_label") and state in {
            "READY",
            "THINKING",
            "AWAITING_PERMISSION",
            "EXECUTING",
            "VERIFYING",
            "SPEAKING",
            "ERROR",
        }:
            self.activity_label.setText(state)

    def _set_busy(self, busy: bool) -> None:
        if self.execute_button is not None:
            self.execute_button.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    @Slot()
    def _voice_not_connected(self) -> None:
        self.response_label.setText(
            "VOICE: text runtime is live; microphone worker is the next integration step."
        )

    def closeEvent(self, event) -> None:
        self.jarvis.unsubscribe("*", self.event_bridge.forward)
        super().closeEvent(event)
