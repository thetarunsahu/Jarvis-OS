from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QLabel, QMessageBox, QPushButton, QFrame, QVBoxLayout

from core.jarvis import Jarvis
from core.state import JarvisState
from interface.dashboard import CYAN, CYAN_DARK, MUTED, PANEL, WHITE, JarvisHUD
from security.permissions import PermissionDecision, PermissionLevel
from voice.voice_manager import VoiceManager
from voice.wake_word import WakeWordDetector


@dataclass
class PermissionPrompt:
    request: Any
    done: threading.Event
    decision: PermissionDecision = PermissionDecision.DENY


class PermissionBridge(QObject):
    """Safely moves permission prompts from a worker thread to the GUI thread."""

    permission_requested = Signal(object)

    def approve(self, request) -> PermissionDecision:
        prompt = PermissionPrompt(request=request, done=threading.Event())
        self.permission_requested.emit(prompt)
        if not prompt.done.wait(timeout=300):
            return PermissionDecision.DENY
        return prompt.decision


class CoreEventBridge(QObject):
    """Forwards core events to Qt signals without touching widgets off-thread."""

    event_received = Signal(str, object)

    def forward(self, event) -> None:
        self.event_received.emit(event.name, event.payload)


class WakeWordBridge(QObject):
    """Qt-safe bridge for the daemon wake-word listener thread."""

    detected = Signal(float)
    stage_changed = Signal(str)
    failed = Signal(str)
    finished = Signal(int)


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


class ListenWorker(QObject):
    recognized = Signal(str)
    stage_changed = Signal(str)
    failed = Signal(str)

    def __init__(self, voice: VoiceManager, duration: float = 8.0) -> None:
        super().__init__()
        self.voice = voice
        self.duration = duration

    @Slot()
    def run(self) -> None:
        try:
            transcript = self.voice.listen(
                duration=self.duration,
                stage_callback=self.stage_changed.emit,
            )
            self.recognized.emit(transcript)
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class SpeechWorker(QObject):
    completed = Signal()
    failed = Signal(str)

    def __init__(self, voice: VoiceManager, text: str) -> None:
        super().__init__()
        self.voice = voice
        self.text = text

    @Slot()
    def run(self) -> None:
        try:
            self.voice.speak(self.text)
            self.completed.emit()
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class JarvisRuntimeHUD(JarvisHUD):
    """Existing HUD wired to the real JARVIS core through background workers."""

    def __init__(self) -> None:
        super().__init__()

        self.jarvis = Jarvis()
        self.voice = VoiceManager()
        self.wake_detector = WakeWordDetector()

        self.request_thread: QThread | None = None
        self.request_worker: RequestWorker | None = None
        self.listen_thread: QThread | None = None
        self.listen_worker: ListenWorker | None = None
        self.speech_thread: QThread | None = None
        self.speech_worker: SpeechWorker | None = None
        self._speak_after_request = False

        self._voice_started_at: float | None = None
        self._request_started_at: float | None = None
        self._last_voice_seconds: float | None = None
        self._last_core_seconds: float | None = None

        self._wake_enabled = self._env_flag("JARVIS_WAKE_WORD_ENABLED", True)
        self._wake_thread: threading.Thread | None = None
        self._wake_stop_event: threading.Event | None = None
        self._wake_generation = 0
        self._closing = False

        self.permission_bridge = PermissionBridge(self)
        self.permission_bridge.permission_requested.connect(
            self._show_permission_dialog
        )
        self.jarvis.set_permission_approver(self.permission_bridge.approve)

        self.event_bridge = CoreEventBridge(self)
        self.event_bridge.event_received.connect(self._handle_core_event)
        self.jarvis.subscribe("*", self.event_bridge.forward)

        self.wake_bridge = WakeWordBridge(self)
        self.wake_bridge.detected.connect(self._on_wake_detected)
        self.wake_bridge.stage_changed.connect(self._on_wake_stage)
        self.wake_bridge.failed.connect(self._on_wake_failed)
        self.wake_bridge.finished.connect(self._on_wake_finished)

        self._install_runtime_panel()
        self._wire_controls()
        self._set_status("READY")
        self._update_wake_button()

        if self._wake_enabled:
            QTimer.singleShot(300, self._arm_wake_word)

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

        self.wake_label = QLabel("WAKE // STARTING" if self._wake_enabled else "WAKE // OFF")
        self.wake_label.setStyleSheet(
            f"color: {CYAN_DARK}; font-size: 9px; letter-spacing: 1px;"
        )

        self.wake_toggle_button = QPushButton()
        self.wake_toggle_button.setFixedHeight(25)
        self.wake_toggle_button.setStyleSheet(
            f"""
            QPushButton {{
                color: {CYAN};
                background: transparent;
                border: 1px solid {CYAN_DARK};
                border-radius: 5px;
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                color: {WHITE};
                border: 1px solid {CYAN};
            }}
            """
        )
        self.wake_toggle_button.clicked.connect(self._toggle_wake_word)

        self.latency_label = QLabel("VOICE -- // CORE --")
        self.latency_label.setStyleSheet(
            f"color: {CYAN_DARK}; font-size: 9px; letter-spacing: 1px;"
        )

        self.response_label = QLabel("JARVIS is connected to the local runtime.")
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet(
            f"color: {WHITE}; font-size: 12px;"
        )

        layout.addWidget(self.runtime_label)
        layout.addWidget(self.activity_label)
        layout.addWidget(self.wake_label)
        layout.addWidget(self.wake_toggle_button)
        layout.addWidget(self.latency_label)
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
        if self.listen_button is None:
            raise RuntimeError("HUD listen button was not found.")

        try:
            self.execute_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.execute_button.clicked.connect(self.execute_command)
        self.input.returnPressed.connect(self.execute_command)

        try:
            self.listen_button.clicked.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.listen_button.clicked.connect(self.start_listening)

    def _operation_active(self) -> bool:
        return any(
            thread is not None
            for thread in (
                self.request_thread,
                self.listen_thread,
                self.speech_thread,
            )
        )

    @Slot()
    def execute_command(self) -> None:
        command = self.input.text().strip()
        if not command or self._operation_active():
            return

        self._disarm_wake_word(wait_ms=250)
        self.input.clear()
        self.response_label.setText(f"YOU: {command}")
        self.activity_label.setText("REQUEST ACCEPTED")
        self._last_voice_seconds = None
        self._update_latency_label()
        self._set_busy(True)
        self._start_request(command, speak_response=False)

    @Slot()
    def start_listening(self) -> None:
        if self._operation_active():
            return

        self._disarm_wake_word(wait_ms=600)
        self._begin_listening(activated_by_wake=False)

    def _begin_listening(self, *, activated_by_wake: bool) -> None:
        if self._operation_active() or self._closing:
            return

        self._set_busy(True)
        self._voice_started_at = time.perf_counter()
        self._last_voice_seconds = None
        self._last_core_seconds = None
        self._update_latency_label()
        if activated_by_wake:
            self.response_label.setText("WAKE: detected — listening for your command...")
        else:
            self.response_label.setText("VOICE: listening...")
        self.jarvis.set_runtime_state(JarvisState.LISTENING)

        thread = QThread(self)
        worker = ListenWorker(self.voice, duration=8.0)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.stage_changed.connect(self._on_voice_stage)
        worker.recognized.connect(self._on_voice_recognized)
        worker.failed.connect(self._on_voice_failed)
        worker.recognized.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.recognized.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._release_listen_worker)

        self.listen_thread = thread
        self.listen_worker = worker
        thread.start()

    @Slot(str)
    def _on_voice_stage(self, stage: str) -> None:
        stage = stage.strip().lower()
        if stage == "listening":
            self.jarvis.set_runtime_state(JarvisState.LISTENING)
            self.activity_label.setText("LISTENING")
            return

        if stage == "loading_stt":
            self.jarvis.set_runtime_state(JarvisState.TRANSCRIBING)
            self.activity_label.setText("LOADING LOCAL STT")
            self.response_label.setText("VOICE: loading local speech model...")
            return

        if stage == "transcribing":
            self.jarvis.set_runtime_state(JarvisState.TRANSCRIBING)
            self.activity_label.setText("TRANSCRIBING")
            self.response_label.setText("VOICE: transcribing locally...")

    @Slot(str)
    def _on_voice_recognized(self, transcript: str) -> None:
        if self._voice_started_at is not None:
            self._last_voice_seconds = time.perf_counter() - self._voice_started_at
            self._voice_started_at = None
            self._update_latency_label()

        transcript = transcript.strip()
        if not transcript:
            self.response_label.setText(
                "VOICE: I couldn't understand that. Say 'Hey Jarvis' or press LISTEN and try again."
            )
            self.jarvis.set_runtime_state(JarvisState.READY)
            self._set_busy(False)
            self._schedule_wake_rearm()
            return

        self.response_label.setText(f"YOU (VOICE): {transcript}")
        self.input.setText(transcript)
        self._start_request(transcript, speak_response=True)

    @Slot(str)
    def _on_voice_failed(self, message: str) -> None:
        if self._voice_started_at is not None:
            self._last_voice_seconds = time.perf_counter() - self._voice_started_at
            self._voice_started_at = None
            self._update_latency_label()

        self.response_label.setText(f"VOICE ERROR: {message}")
        self.jarvis.set_runtime_state(JarvisState.ERROR)
        self._set_busy(False)
        self._schedule_wake_rearm()

    @Slot()
    def _release_listen_worker(self) -> None:
        self.listen_thread = None
        self.listen_worker = None

    def _start_request(self, command: str, *, speak_response: bool) -> None:
        if self.request_thread is not None:
            return

        self._speak_after_request = speak_response
        self._request_started_at = time.perf_counter()

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
        thread.finished.connect(self._release_request_worker)

        self.request_thread = thread
        self.request_worker = worker
        thread.start()

    @Slot(str)
    def _on_request_finished(self, response: str) -> None:
        if self._request_started_at is not None:
            self._last_core_seconds = time.perf_counter() - self._request_started_at
            self._request_started_at = None
            self._update_latency_label()

        if response:
            self.response_label.setText(f"JARVIS: {response}")

        if self._speak_after_request and response:
            self._start_speaking(response)
        else:
            self._set_busy(False)
            self._schedule_wake_rearm()

    @Slot(str)
    def _on_request_failed(self, message: str) -> None:
        if self._request_started_at is not None:
            self._last_core_seconds = time.perf_counter() - self._request_started_at
            self._request_started_at = None
            self._update_latency_label()

        self.response_label.setText(f"JARVIS ERROR: {message}")
        self.jarvis.set_runtime_state(JarvisState.ERROR)
        self._set_busy(False)
        self._schedule_wake_rearm()

    @Slot()
    def _release_request_worker(self) -> None:
        self.request_thread = None
        self.request_worker = None
        self._speak_after_request = False

    def _start_speaking(self, text: str) -> None:
        if self.speech_thread is not None:
            return

        self.jarvis.set_runtime_state(JarvisState.SPEAKING)

        thread = QThread(self)
        worker = SpeechWorker(self.voice, text)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.completed.connect(self._on_speech_completed)
        worker.failed.connect(self._on_speech_failed)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._release_speech_worker)

        self.speech_thread = thread
        self.speech_worker = worker
        thread.start()

    @Slot()
    def _on_speech_completed(self) -> None:
        self.jarvis.set_runtime_state(JarvisState.READY)
        self._set_busy(False)
        self._schedule_wake_rearm()

    @Slot(str)
    def _on_speech_failed(self, message: str) -> None:
        self.activity_label.setText(f"VOICE ERROR // {message}")
        self.jarvis.set_runtime_state(JarvisState.ERROR)
        self._set_busy(False)
        self._schedule_wake_rearm()

    @Slot()
    def _release_speech_worker(self) -> None:
        self.speech_thread = None
        self.speech_worker = None

    @Slot()
    def _toggle_wake_word(self) -> None:
        if self._wake_enabled:
            self._wake_enabled = False
            self._disarm_wake_word(wait_ms=400)
            self.wake_label.setText("WAKE // OFF")
            if not self._operation_active():
                self.jarvis.set_runtime_state(JarvisState.READY)
        else:
            self._wake_enabled = True
            self.wake_label.setText("WAKE // STARTING")
            self._arm_wake_word()
        self._update_wake_button()

    def _arm_wake_word(self) -> None:
        if (
            not self._wake_enabled
            or self._closing
            or self._operation_active()
        ):
            return

        thread = self._wake_thread
        if thread is not None and thread.is_alive():
            return

        self._wake_generation += 1
        generation = self._wake_generation
        stop_event = threading.Event()
        self._wake_stop_event = stop_event

        thread = threading.Thread(
            target=self._wake_loop,
            args=(generation, stop_event),
            name="jarvis-wake-word",
            daemon=True,
        )
        self._wake_thread = thread
        self.wake_label.setText("WAKE // STARTING")
        thread.start()

    def _wake_loop(
        self,
        generation: int,
        stop_event: threading.Event,
    ) -> None:
        try:
            detection = self.wake_detector.wait_for_wake_word(
                stop_event,
                stage_callback=self.wake_bridge.stage_changed.emit,
            )
            if detection is not None and not stop_event.is_set():
                self.wake_bridge.detected.emit(float(detection.score))
        except Exception as error:
            self.wake_bridge.failed.emit(f"{type(error).__name__}: {error}")
        finally:
            self.wake_bridge.finished.emit(generation)

    @Slot(str)
    def _on_wake_stage(self, stage: str) -> None:
        if not self._wake_enabled or self._closing:
            return

        stage = stage.strip().lower()
        if stage == "wake_loading":
            self.wake_label.setText("WAKE // LOADING MODEL")
            if not self._operation_active():
                self.activity_label.setText("LOADING WAKE WORD")
            return

        if stage == "wake_armed":
            self.wake_label.setText("WAKE // ARMED — SAY 'HEY JARVIS'")
            if not self._operation_active():
                self.jarvis.set_runtime_state(JarvisState.ARMED)
                self.activity_label.setText("ARMED // SAY 'HEY JARVIS'")
            return

        if stage == "wake_detected":
            self.wake_label.setText("WAKE // DETECTED")

    @Slot(float)
    def _on_wake_detected(self, score: float) -> None:
        if (
            not self._wake_enabled
            or self._closing
            or self._operation_active()
        ):
            return

        self.activity_label.setText(f"WAKE DETECTED // {score:.2f}")
        self._begin_listening(activated_by_wake=True)

    @Slot(str)
    def _on_wake_failed(self, message: str) -> None:
        if self._closing:
            return

        self._wake_enabled = False
        self._update_wake_button()
        self.wake_label.setText("WAKE // ERROR")
        if not self._operation_active():
            self.jarvis.set_runtime_state(JarvisState.READY)
            self.response_label.setText(
                f"WAKE ERROR: {message}. Manual LISTEN still works."
            )

    @Slot(int)
    def _on_wake_finished(self, generation: int) -> None:
        if generation != self._wake_generation:
            return

        self._wake_thread = None
        self._wake_stop_event = None

        if (
            self._wake_enabled
            and not self._closing
            and not self._operation_active()
        ):
            QTimer.singleShot(350, self._arm_wake_word)

    def _disarm_wake_word(self, *, wait_ms: int = 0) -> None:
        stop_event = self._wake_stop_event
        thread = self._wake_thread

        if stop_event is not None:
            stop_event.set()

        if (
            thread is not None
            and thread.is_alive()
            and wait_ms > 0
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=wait_ms / 1000.0)

        if thread is not None and not thread.is_alive():
            self._wake_thread = None
            self._wake_stop_event = None

    def _schedule_wake_rearm(self) -> None:
        if self._wake_enabled and not self._closing:
            QTimer.singleShot(300, self._arm_wake_word)

    def _update_wake_button(self) -> None:
        if hasattr(self, "wake_toggle_button"):
            state = "ON" if self._wake_enabled else "OFF"
            self.wake_toggle_button.setText(f"WAKE WORD: {state}")

    @Slot(object)
    def _show_permission_dialog(self, prompt: PermissionPrompt) -> None:
        request = prompt.request
        args = request.arguments or {}

        details = "\n".join(
            f"{key}: {value}" for key, value in args.items()
        ) or "No arguments"

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("JARVIS Permission Request")
        box.setText(
            f"JARVIS wants to run: {request.tool_name}\n\n"
            f"Risk: {request.level.value}\n"
            f"Reason: {request.reason}\n\n"
            f"Arguments:\n{details}"
        )

        allow_once = box.addButton("Allow once", QMessageBox.AcceptRole)
        allow_session = None
        if request.level == PermissionLevel.CONFIRM:
            allow_session = box.addButton(
                "Allow for session",
                QMessageBox.ActionRole,
            )
        deny = box.addButton("Deny", QMessageBox.RejectRole)
        box.setDefaultButton(deny)
        box.exec()

        clicked = box.clickedButton()
        if clicked is allow_session:
            prompt.decision = PermissionDecision.ALLOW_SESSION
        elif clicked is allow_once:
            prompt.decision = PermissionDecision.ALLOW
        else:
            prompt.decision = PermissionDecision.DENY

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
            "ARMED",
            "LISTENING",
            "TRANSCRIBING",
            "THINKING",
            "AWAITING_PERMISSION",
            "EXECUTING",
            "VERIFYING",
            "SPEAKING",
            "ERROR",
        }:
            self.activity_label.setText(state)

    def _update_latency_label(self) -> None:
        if not hasattr(self, "latency_label"):
            return

        voice = (
            f"{self._last_voice_seconds:.2f}s"
            if self._last_voice_seconds is not None
            else "--"
        )
        core = (
            f"{self._last_core_seconds:.2f}s"
            if self._last_core_seconds is not None
            else "--"
        )
        self.latency_label.setText(f"VOICE {voice} // CORE {core}")

    def _set_busy(self, busy: bool) -> None:
        if self.execute_button is not None:
            self.execute_button.setEnabled(not busy)
        if self.listen_button is not None:
            self.listen_button.setEnabled(not busy)
        self.input.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    @staticmethod
    def _env_flag(name: str, default: bool) -> bool:
        fallback = "1" if default else "0"
        value = os.getenv(name, fallback).strip().lower()
        return value not in {"0", "false", "off", "no"}

    def closeEvent(self, event) -> None:
        self._closing = True
        self._wake_enabled = False
        self._disarm_wake_word(wait_ms=800)
        self.jarvis.unsubscribe("*", self.event_bridge.forward)
        super().closeEvent(event)
