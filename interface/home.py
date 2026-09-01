import html
import math
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


BG = "#080b10"
SURFACE = "#0f141b"
SURFACE_2 = "#121923"
BORDER = "#202b38"
TEXT = "#edf4f8"
MUTED = "#7f8d9b"
ACCENT = "#6ee7f9"
ACCENT_SOFT = "#b6f3fb"
SUCCESS = "#7be0ae"
WARNING = "#f5c76b"


class Surface(QFrame):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("surface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(10)

        if title:
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            self.layout.addWidget(label)


class PresenceCore(QWidget):
    """Quiet animated JARVIS presence for the Home experience."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._state = "idle"
        self.setMinimumSize(220, 220)
        self.setMaximumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(32)

    def set_state(self, state):
        self._state = state or "idle"
        self.update()

    def _tick(self):
        speed = 0.09 if self._state in {"thinking", "working"} else 0.045
        self._phase = (self._phase + speed) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) * 0.25
        pulse = 4 + ((math.sin(self._phase) + 1) * 2.5)

        painter.setPen(QPen(QColor(ACCENT).darker(180), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            QRectF(
                center.x() - radius - 26 - pulse,
                center.y() - radius - 26 - pulse,
                (radius + 26 + pulse) * 2,
                (radius + 26 + pulse) * 2,
            )
        )

        painter.setPen(QPen(QColor(ACCENT), 2.0))
        start = int((self._phase * 180 / math.pi) * 16)
        painter.drawArc(
            QRectF(
                center.x() - radius - 14,
                center.y() - radius - 14,
                (radius + 14) * 2,
                (radius + 14) * 2,
            ),
            start,
            112 * 16,
        )
        painter.drawArc(
            QRectF(
                center.x() - radius - 14,
                center.y() - radius - 14,
                (radius + 14) * 2,
                (radius + 14) * 2,
            ),
            start + 180 * 16,
            72 * 16,
        )

        glow = QColor(ACCENT)
        glow.setAlpha(55)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(
            QRectF(
                center.x() - radius - pulse,
                center.y() - radius - pulse,
                (radius + pulse) * 2,
                (radius + pulse) * 2,
            )
        )

        painter.setBrush(QBrush(QColor("#122d37")))
        painter.drawEllipse(
            QRectF(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
            )
        )

        painter.setBrush(QBrush(QColor(ACCENT_SOFT)))
        core = radius * 0.28
        painter.drawEllipse(
            QRectF(
                center.x() - core,
                center.y() - core,
                core * 2,
                core * 2,
            )
        )


class JarvisHome(QWidget):
    command_submitted = Signal(str)
    diagnostics_requested = Signal()
    workspace_resume_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS")
        self.setMinimumSize(1180, 720)
        self._build_ui()
        self._apply_style()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("JARVIS")
        title.setObjectName("brand")
        subtitle = QLabel("PERSONAL AI OPERATING ENVIRONMENT")
        subtitle.setObjectName("eyebrow")
        brand.addWidget(title)
        brand.addWidget(subtitle)

        status_wrap = QHBoxLayout()
        self.model_label = QLabel("AUTO ROUTER")
        self.model_label.setObjectName("pill")
        self.status_label = QLabel("● ONLINE")
        self.status_label.setObjectName("statusPill")
        self.clock_label = QLabel()
        self.clock_label.setObjectName("clock")
        status_wrap.addWidget(self.model_label)
        status_wrap.addWidget(self.status_label)
        status_wrap.addSpacing(12)
        status_wrap.addWidget(self.clock_label)

        header.addLayout(brand)
        header.addStretch()
        header.addLayout(status_wrap)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(16)

        left = Surface("RECENT WORK")
        left.setMinimumWidth(270)
        left.setMaximumWidth(340)

        self.workspace_status = QLabel("NO SAVED CONTEXT")
        self.workspace_status.setObjectName("eyebrow")
        left.layout.addWidget(self.workspace_status)

        self.workspace_title = QLabel("No saved workspace yet")
        self.workspace_title.setObjectName("cardTitle")
        self.workspace_title.setWordWrap(True)
        left.layout.addWidget(self.workspace_title)

        self.workspace_meta = QLabel(
            "Register or open a project through JARVIS to make it resumable."
        )
        self.workspace_meta.setWordWrap(True)
        self.workspace_meta.setObjectName("body")
        left.layout.addWidget(self.workspace_meta)

        self.workspace_next = QLabel("Next action will appear here when captured.")
        self.workspace_next.setWordWrap(True)
        self.workspace_next.setObjectName("workspaceNext")
        left.layout.addWidget(self.workspace_next)
        left.layout.addStretch()

        self.resume_button = QPushButton("Continue workspace")
        self.resume_button.setObjectName("primaryButton")
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.workspace_resume_requested.emit)
        left.layout.addWidget(self.resume_button)

        self.context_button = QPushButton("View workspace context")
        self.context_button.setEnabled(False)
        self.context_button.clicked.connect(lambda: self.command_submitted.emit("workspace"))
        left.layout.addWidget(self.context_button)

        center = Surface()
        center.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        presence_header = QHBoxLayout()
        presence_copy = QVBoxLayout()
        self.greeting = QLabel("What are we working on?")
        self.greeting.setObjectName("hero")
        self.presence_status = QLabel("SYSTEM READY")
        self.presence_status.setObjectName("eyebrow")
        presence_copy.addWidget(self.greeting)
        presence_copy.addWidget(self.presence_status)
        presence_header.addLayout(presence_copy)
        presence_header.addStretch()
        center.layout.addLayout(presence_header)

        self.presence = PresenceCore()
        center.layout.addWidget(self.presence, alignment=Qt.AlignHCenter)

        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(8)
        continue_action = QPushButton("Continue")
        continue_action.setObjectName("quickButton")
        continue_action.clicked.connect(self.workspace_resume_requested.emit)
        self.continue_action = continue_action
        self.continue_action.setEnabled(False)

        brief_action = QPushButton("Today's brief")
        brief_action.setObjectName("quickButton")
        brief_action.clicked.connect(lambda: self.command_submitted.emit("daily brief"))

        tasks_action = QPushButton("Active tasks")
        tasks_action.setObjectName("quickButton")
        tasks_action.clicked.connect(lambda: self.command_submitted.emit("tasks"))

        files_action = QPushButton("File intelligence")
        files_action.setObjectName("quickButton")
        files_action.clicked.connect(lambda: self.command_submitted.emit("file index status"))

        quick_actions.addStretch()
        quick_actions.addWidget(continue_action)
        quick_actions.addWidget(brief_action)
        quick_actions.addWidget(tasks_action)
        quick_actions.addWidget(files_action)
        quick_actions.addStretch()
        center.layout.addLayout(quick_actions)

        self.conversation = QTextBrowser()
        self.conversation.setObjectName("conversation")
        self.conversation.setOpenExternalLinks(True)
        center.layout.addWidget(self.conversation, 1)
        self.append_message(
            "jarvis",
            "I'm ready. Continue your workspace, ask for context, or give me a new goal.",
        )

        command_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask JARVIS or do anything…")
        self.input.returnPressed.connect(self._submit_command)
        self.listen_button = QPushButton("◉")
        self.listen_button.setToolTip("Voice input will connect here")
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.clicked.connect(self._submit_command)
        command_row.addWidget(self.input, 1)
        command_row.addWidget(self.listen_button)
        command_row.addWidget(self.send_button)
        center.layout.addLayout(command_row)

        right_column = QVBoxLayout()
        right_column.setSpacing(16)

        today = Surface("TODAY")
        today.setMinimumWidth(280)
        today.setMaximumWidth(370)
        self.today_label = QLabel("No active commitments loaded yet.")
        self.today_label.setObjectName("body")
        self.today_label.setWordWrap(True)
        today.layout.addWidget(self.today_label)

        tasks = Surface("ACTIVE WORK")
        self.tasks_label = QLabel("No active JARVIS tasks.")
        self.tasks_label.setObjectName("body")
        self.tasks_label.setWordWrap(True)
        tasks.layout.addWidget(self.tasks_label)

        agents = Surface("AGENTS")
        self.agents_label = QLabel("No agent currently running.")
        self.agents_label.setObjectName("body")
        self.agents_label.setWordWrap(True)
        agents.layout.addWidget(self.agents_label)

        approvals = Surface("APPROVALS")
        self.approvals_label = QLabel("No pending approvals.")
        self.approvals_label.setObjectName("body")
        self.approvals_label.setWordWrap(True)
        approvals.layout.addWidget(self.approvals_label)

        right_column.addWidget(today)
        right_column.addWidget(tasks)
        right_column.addWidget(agents)
        right_column.addWidget(approvals)
        right_column.addStretch()

        content.addWidget(left)
        content.addWidget(center, 1)
        content.addLayout(right_column)
        root.addLayout(content, 1)

        self.session_strip = QLabel("SESSION CONTINUITY  •  WAITING FOR WORKSPACE")
        self.session_strip.setObjectName("sessionStrip")
        self.session_strip.setAlignment(Qt.AlignCenter)
        root.addWidget(self.session_strip)

        dock = QFrame()
        dock.setObjectName("dock")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(12, 8, 12, 8)
        dock_layout.setSpacing(8)
        dock_layout.addStretch()

        for label in ["Home", "Projects", "Files", "Code", "Browser", "Agents", "Terminal"]:
            button = QPushButton(label)
            button.setObjectName("dockButton")
            if label != "Home":
                button.setEnabled(False)
            dock_layout.addWidget(button)

        diagnostics = QPushButton("Diagnostics")
        diagnostics.setObjectName("dockButton")
        diagnostics.clicked.connect(self.diagnostics_requested.emit)
        dock_layout.addWidget(diagnostics)

        settings = QPushButton("Settings")
        settings.setObjectName("dockButton")
        settings.setEnabled(False)
        dock_layout.addWidget(settings)
        dock_layout.addStretch()

        root.addWidget(dock)

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BG};
                color: {TEXT};
                font-family: 'Segoe UI';
                font-size: 13px;
            }}

            QFrame#surface {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}

            QLabel#brand {{
                color: {TEXT};
                font-size: 25px;
                font-weight: 700;
                letter-spacing: 5px;
            }}

            QLabel#hero {{
                color: {TEXT};
                font-size: 25px;
                font-weight: 650;
            }}

            QLabel#eyebrow, QLabel#sectionTitle {{
                color: {MUTED};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#cardTitle {{
                color: {ACCENT_SOFT};
                font-size: 17px;
                font-weight: 650;
            }}

            QLabel#body, QLabel#muted {{
                color: {MUTED};
                line-height: 1.4;
            }}

            QLabel#workspaceNext {{
                color: {ACCENT_SOFT};
                background: #0c1218;
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 10px;
            }}

            QLabel#pill, QLabel#statusPill {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 7px 11px;
                color: {ACCENT_SOFT};
                font-size: 10px;
                font-weight: 700;
            }}

            QLabel#statusPill {{
                color: {SUCCESS};
            }}

            QLabel#clock {{
                color: {MUTED};
                font-size: 12px;
            }}

            QLabel#sessionStrip {{
                background: #0b1117;
                border: 1px solid #18232e;
                border-radius: 10px;
                color: {MUTED};
                padding: 7px 12px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QTextBrowser#conversation {{
                background: transparent;
                border: none;
                color: {TEXT};
                padding: 8px 2px;
                font-size: 14px;
            }}

            QLineEdit {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 14px;
                padding: 13px 15px;
                color: {TEXT};
                selection-background-color: #245d68;
                font-size: 14px;
            }}

            QLineEdit:focus {{
                border: 1px solid #3d7985;
            }}

            QPushButton {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 12px;
                padding: 10px 15px;
                color: {TEXT};
                font-weight: 600;
            }}

            QPushButton:hover {{
                border-color: #3c5668;
                background: #17212c;
            }}

            QPushButton:disabled {{
                color: #4f5963;
                background: #0d1218;
            }}

            QPushButton#primaryButton {{
                background: #15333d;
                border-color: #2f6672;
                color: {ACCENT_SOFT};
            }}

            QPushButton#primaryButton:hover {{
                background: #1c4652;
                border-color: {ACCENT};
            }}

            QPushButton#quickButton {{
                padding: 7px 11px;
                color: {MUTED};
                font-size: 11px;
            }}

            QFrame#dock {{
                background: #0c1117;
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}

            QPushButton#dockButton {{
                min-width: 68px;
                padding: 8px 11px;
                background: transparent;
            }}
            """
        )

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%a, %d %b  •  %I:%M %p"))

    def _submit_command(self):
        command = self.input.text().strip()
        if not command:
            return
        self.input.clear()
        self.append_message("you", command)
        self.command_submitted.emit(command)

    def append_message(self, role, text):
        safe = html.escape(str(text)).replace("\n", "<br>")
        if role == "you":
            block = (
                f"<div style='margin:10px 0 4px 70px; color:{TEXT};'>"
                f"<span style='color:{MUTED}; font-size:10px;'>YOU</span><br>"
                f"{safe}</div>"
            )
        else:
            block = (
                f"<div style='margin:10px 70px 4px 0; color:{TEXT};'>"
                f"<span style='color:{ACCENT}; font-size:10px;'>JARVIS</span><br>"
                f"{safe}</div>"
            )
        self.conversation.append(block)
        bar = self.conversation.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_runtime_status(self, text, state="idle"):
        self.presence_status.setText(str(text).upper())
        self.presence.set_state(state)

    def set_workspace(self, name, details, resumable=True, next_action=None):
        self.workspace_status.setText("RESUMABLE SESSION" if resumable else "WORKSPACE CONTEXT")
        self.workspace_title.setText(str(name))
        self.workspace_meta.setText("\n".join(details) if details else "Context available.")
        self.workspace_next.setText(
            f"Next: {next_action}" if next_action else "Next: Continue from the latest saved session."
        )
        self.resume_button.setEnabled(bool(resumable))
        self.context_button.setEnabled(True)
        self.continue_action.setEnabled(bool(resumable))
        self.session_strip.setText(
            "SESSION CONTINUITY  •  READY TO RESUME" if resumable
            else "SESSION CONTINUITY  •  CONTEXT AVAILABLE"
        )

    def set_workspace_empty(self):
        self.workspace_status.setText("NO SAVED CONTEXT")
        self.workspace_title.setText("No saved workspace yet")
        self.workspace_meta.setText("Register or open a project through JARVIS to make it resumable.")
        self.workspace_next.setText("Next action will appear here when captured.")
        self.resume_button.setEnabled(False)
        self.context_button.setEnabled(False)
        self.continue_action.setEnabled(False)
        self.session_strip.setText("SESSION CONTINUITY  •  WAITING FOR WORKSPACE")

    def set_tasks(self, lines):
        self.tasks_label.setText("\n".join(lines) if lines else "No active JARVIS tasks.")

    def set_agents(self, lines):
        self.agents_label.setText("\n".join(lines) if lines else "No agent currently running.")

    def set_approvals(self, lines):
        self.approvals_label.setText("\n".join(lines) if lines else "No pending approvals.")

    def set_today(self, text):
        self.today_label.setText(text or "No active commitments loaded yet.")
