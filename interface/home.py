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


BG = "#070a0f"
SURFACE = "#0e141c"
SURFACE_2 = "#111a24"
SURFACE_3 = "#0a1017"
BORDER = "#1d2a38"
BORDER_SOFT = "#15202b"
TEXT = "#f3f7fa"
MUTED = "#8392a2"
MUTED_2 = "#5e6d7c"
ACCENT = "#72e8f7"
ACCENT_SOFT = "#bff7fc"
SUCCESS = "#7fe5b1"
WARNING = "#f1c96d"


class Surface(QFrame):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("surface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 20, 22, 20)
        self.layout.setSpacing(12)

        if title:
            label = QLabel(title)
            label.setObjectName("sectionTitle")
            self.layout.addWidget(label)


class PresenceCore(QWidget):
    """Calm animated JARVIS presence rather than a decorative dashboard gauge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._state = "idle"
        self.setMinimumSize(250, 250)
        self.setMaximumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(32)

    def set_state(self, state):
        self._state = state or "idle"
        self.update()

    def _tick(self):
        speed = 0.1 if self._state in {"thinking", "working"} else 0.038
        self._phase = (self._phase + speed) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        radius = min(self.width(), self.height()) * 0.22
        pulse = 3 + ((math.sin(self._phase) + 1) * 3.5)

        # Outer quiet orbit.
        outer = radius + 48 + pulse
        outer_color = QColor(ACCENT)
        outer_color.setAlpha(45)
        painter.setPen(QPen(outer_color, 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            QRectF(center.x() - outer, center.y() - outer, outer * 2, outer * 2)
        )

        # Two asymmetric activity arcs.
        arc_radius = radius + 29
        painter.setPen(QPen(QColor(ACCENT), 2.2))
        angle = int((self._phase * 180 / math.pi) * 16)
        arc_rect = QRectF(
            center.x() - arc_radius,
            center.y() - arc_radius,
            arc_radius * 2,
            arc_radius * 2,
        )
        painter.drawArc(arc_rect, angle, 96 * 16)
        painter.drawArc(arc_rect, angle + 184 * 16, 58 * 16)

        inner_arc = radius + 15
        inner_color = QColor(ACCENT_SOFT)
        inner_color.setAlpha(120)
        painter.setPen(QPen(inner_color, 1.1))
        painter.drawArc(
            QRectF(
                center.x() - inner_arc,
                center.y() - inner_arc,
                inner_arc * 2,
                inner_arc * 2,
            ),
            -angle // 2,
            132 * 16,
        )

        # Soft core glow.
        glow = QColor(ACCENT)
        glow.setAlpha(34 if self._state == "idle" else 58)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        glow_radius = radius + 12 + pulse
        painter.drawEllipse(
            QRectF(
                center.x() - glow_radius,
                center.y() - glow_radius,
                glow_radius * 2,
                glow_radius * 2,
            )
        )

        painter.setBrush(QBrush(QColor("#102733")))
        painter.drawEllipse(
            QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        )

        middle = radius * 0.54
        painter.setBrush(QBrush(QColor("#163d49")))
        painter.drawEllipse(
            QRectF(center.x() - middle, center.y() - middle, middle * 2, middle * 2)
        )

        core = radius * 0.22
        painter.setBrush(QBrush(QColor(ACCENT_SOFT)))
        painter.drawEllipse(
            QRectF(center.x() - core, center.y() - core, core * 2, core * 2)
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
        root.setContentsMargins(30, 24, 30, 24)
        root.setSpacing(18)

        # Header: brand and state only. No telemetry clutter.
        header = QHBoxLayout()
        header.setSpacing(14)

        brand = QVBoxLayout()
        brand.setSpacing(2)
        title = QLabel("JARVIS")
        title.setObjectName("brand")
        subtitle = QLabel("PERSONAL AI OPERATING ENVIRONMENT")
        subtitle.setObjectName("eyebrow")
        brand.addWidget(title)
        brand.addWidget(subtitle)

        self.model_label = QLabel("AUTO ROUTER")
        self.model_label.setObjectName("pill")
        self.status_label = QLabel("ONLINE")
        self.status_label.setObjectName("statusPill")
        self.clock_label = QLabel()
        self.clock_label.setObjectName("clock")

        header.addLayout(brand)
        header.addStretch()
        header.addWidget(self.model_label)
        header.addWidget(self.status_label)
        header.addSpacing(8)
        header.addWidget(self.clock_label)
        root.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(18)

        # Left: one useful resumable work surface, not a miniature dashboard.
        workspace = Surface("CURRENT WORKSPACE")
        workspace.setMinimumWidth(310)
        workspace.setMaximumWidth(380)

        self.workspace_status = QLabel("NO SAVED CONTEXT")
        self.workspace_status.setObjectName("workspaceStatus")
        workspace.layout.addWidget(self.workspace_status)

        self.workspace_title = QLabel("No saved workspace yet")
        self.workspace_title.setObjectName("workspaceTitle")
        self.workspace_title.setWordWrap(True)
        workspace.layout.addWidget(self.workspace_title)

        self.workspace_meta = QLabel(
            "Open or register a project through JARVIS. The latest work context will live here."
        )
        self.workspace_meta.setObjectName("workspaceMeta")
        self.workspace_meta.setWordWrap(True)
        workspace.layout.addWidget(self.workspace_meta)

        next_label = QLabel("NEXT ACTION")
        next_label.setObjectName("sectionTitle")
        workspace.layout.addWidget(next_label)

        self.workspace_next = QLabel("No next action captured yet.")
        self.workspace_next.setObjectName("workspaceNext")
        self.workspace_next.setWordWrap(True)
        workspace.layout.addWidget(self.workspace_next)

        workspace.layout.addStretch()

        self.session_strip = QLabel("SESSION CONTINUITY · WAITING")
        self.session_strip.setObjectName("sessionStrip")
        self.session_strip.setWordWrap(True)
        workspace.layout.addWidget(self.session_strip)

        self.resume_button = QPushButton("Continue workspace")
        self.resume_button.setObjectName("primaryButton")
        self.resume_button.setMinimumHeight(48)
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.workspace_resume_requested.emit)
        workspace.layout.addWidget(self.resume_button)

        self.context_button = QPushButton("View full context")
        self.context_button.setObjectName("secondaryButton")
        self.context_button.setEnabled(False)
        self.context_button.clicked.connect(lambda: self.command_submitted.emit("workspace"))
        workspace.layout.addWidget(self.context_button)

        # Center: JARVIS presence + conversation. This is the product focus.
        center_column = QVBoxLayout()
        center_column.setSpacing(18)

        hero = Surface()
        hero.setObjectName("heroSurface")
        hero.setMinimumHeight(300)
        hero.setMaximumHeight(360)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(18)

        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(10)

        core_label = QLabel("JARVIS CORE")
        core_label.setObjectName("accentEyebrow")
        self.greeting = QLabel("Ready when you are.")
        self.greeting.setObjectName("heroTitle")
        self.greeting.setWordWrap(True)
        hero_body = QLabel(
            "Continue where you stopped, ask for context, or hand JARVIS a new goal."
        )
        hero_body.setObjectName("heroBody")
        hero_body.setWordWrap(True)
        self.presence_status = QLabel("SYSTEM READY")
        self.presence_status.setObjectName("presenceStatus")

        hero_copy.addStretch()
        hero_copy.addWidget(core_label)
        hero_copy.addWidget(self.greeting)
        hero_copy.addWidget(hero_body)
        hero_copy.addWidget(self.presence_status)
        hero_copy.addSpacing(8)

        quick_actions = QHBoxLayout()
        quick_actions.setSpacing(8)

        self.continue_action = QPushButton("Continue")
        self.continue_action.setObjectName("primaryCompact")
        self.continue_action.setEnabled(False)
        self.continue_action.clicked.connect(self.workspace_resume_requested.emit)

        brief_action = QPushButton("Today")
        brief_action.setObjectName("quickButton")
        brief_action.clicked.connect(lambda: self.command_submitted.emit("daily brief"))

        tasks_action = QPushButton("Tasks")
        tasks_action.setObjectName("quickButton")
        tasks_action.clicked.connect(lambda: self.command_submitted.emit("tasks"))

        files_action = QPushButton("Files")
        files_action.setObjectName("quickButton")
        files_action.clicked.connect(lambda: self.command_submitted.emit("file index status"))

        quick_actions.addWidget(self.continue_action)
        quick_actions.addWidget(brief_action)
        quick_actions.addWidget(tasks_action)
        quick_actions.addWidget(files_action)
        quick_actions.addStretch()
        hero_copy.addLayout(quick_actions)
        hero_copy.addStretch()

        self.presence = PresenceCore()
        hero_row.addLayout(hero_copy, 1)
        hero_row.addWidget(self.presence, 0, Qt.AlignCenter)
        hero.layout.addLayout(hero_row)
        center_column.addWidget(hero)

        thread = Surface("CONVERSATION")
        thread.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.conversation = QTextBrowser()
        self.conversation.setObjectName("conversation")
        self.conversation.setOpenExternalLinks(True)
        self.conversation.setMinimumHeight(220)
        thread.layout.addWidget(self.conversation, 1)
        self.append_message(
            "jarvis",
            "I am ready. Your project context, tasks and tools are available from this workspace.",
        )

        command_row = QHBoxLayout()
        command_row.setSpacing(10)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask JARVIS, continue work, find a file, start a task...")
        self.input.setMinimumHeight(50)
        self.input.returnPressed.connect(self._submit_command)

        self.listen_button = QPushButton("Voice")
        self.listen_button.setObjectName("iconButton")
        self.listen_button.setToolTip("Voice input integration")
        self.listen_button.setMinimumHeight(50)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.setMinimumHeight(50)
        self.send_button.clicked.connect(self._submit_command)

        command_row.addWidget(self.input, 1)
        command_row.addWidget(self.listen_button)
        command_row.addWidget(self.send_button)
        thread.layout.addLayout(command_row)
        center_column.addWidget(thread, 1)

        # Right: useful live context with fewer, stronger surfaces.
        right_column = QVBoxLayout()
        right_column.setSpacing(18)

        today = Surface("TODAY")
        today.setMinimumWidth(310)
        today.setMaximumWidth(390)
        self.today_label = QLabel("No active commitments loaded yet.")
        self.today_label.setObjectName("body")
        self.today_label.setWordWrap(True)
        today.layout.addWidget(self.today_label)

        activity = Surface("LIVE ACTIVITY")
        activity_title = QLabel("Active work")
        activity_title.setObjectName("miniTitle")
        self.tasks_label = QLabel("No active JARVIS tasks.")
        self.tasks_label.setObjectName("body")
        self.tasks_label.setWordWrap(True)
        agents_title = QLabel("Agents")
        agents_title.setObjectName("miniTitle")
        self.agents_label = QLabel("No agent currently running.")
        self.agents_label.setObjectName("body")
        self.agents_label.setWordWrap(True)

        activity.layout.addWidget(activity_title)
        activity.layout.addWidget(self.tasks_label)
        activity.layout.addSpacing(8)
        activity.layout.addWidget(agents_title)
        activity.layout.addWidget(self.agents_label)

        approvals = Surface("APPROVALS")
        self.approvals_label = QLabel("No pending approvals.")
        self.approvals_label.setObjectName("body")
        self.approvals_label.setWordWrap(True)
        approvals.layout.addWidget(self.approvals_label)

        right_column.addWidget(today)
        right_column.addWidget(activity)
        right_column.addWidget(approvals)
        right_column.addStretch()

        content.addWidget(workspace)
        content.addLayout(center_column, 1)
        content.addLayout(right_column)
        root.addLayout(content, 1)

        # Only expose navigation that does something today.
        dock = QFrame()
        dock.setObjectName("dock")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(14, 9, 14, 9)
        dock_layout.setSpacing(8)
        dock_layout.addStretch()

        home_button = QPushButton("Home")
        home_button.setObjectName("dockActive")
        dock_layout.addWidget(home_button)

        workspace_button = QPushButton("Workspace")
        workspace_button.setObjectName("dockButton")
        workspace_button.clicked.connect(lambda: self.command_submitted.emit("workspace"))
        dock_layout.addWidget(workspace_button)

        files_button = QPushButton("Files")
        files_button.setObjectName("dockButton")
        files_button.clicked.connect(lambda: self.command_submitted.emit("file index status"))
        dock_layout.addWidget(files_button)

        tasks_button = QPushButton("Tasks")
        tasks_button.setObjectName("dockButton")
        tasks_button.clicked.connect(lambda: self.command_submitted.emit("tasks"))
        dock_layout.addWidget(tasks_button)

        diagnostics = QPushButton("Diagnostics")
        diagnostics.setObjectName("dockButton")
        diagnostics.clicked.connect(self.diagnostics_requested.emit)
        dock_layout.addWidget(diagnostics)
        dock_layout.addStretch()

        root.addWidget(dock)

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BG};
                color: {TEXT};
                font-family: 'Segoe UI';
                font-size: 16px;
            }}

            QFrame#surface, QFrame#heroSurface {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 20px;
            }}

            QFrame#heroSurface {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #101821,
                    stop:0.62 #0d141c,
                    stop:1 #0b1118
                );
                border: 1px solid #233445;
            }}

            QLabel#brand {{
                color: {TEXT};
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 6px;
            }}

            QLabel#eyebrow, QLabel#sectionTitle {{
                color: {MUTED};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#accentEyebrow {{
                color: {ACCENT};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 3px;
            }}

            QLabel#heroTitle {{
                color: {TEXT};
                font-size: 34px;
                font-weight: 650;
            }}

            QLabel#heroBody {{
                color: #9aa8b7;
                font-size: 16px;
                line-height: 1.35;
            }}

            QLabel#presenceStatus {{
                color: {ACCENT_SOFT};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#workspaceStatus {{
                color: {SUCCESS};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            QLabel#workspaceTitle {{
                color: {TEXT};
                font-size: 25px;
                font-weight: 650;
            }}

            QLabel#workspaceMeta {{
                color: #94a3b2;
                font-size: 14px;
                line-height: 1.45;
            }}

            QLabel#workspaceNext {{
                color: {TEXT};
                background: {SURFACE_3};
                border: 1px solid #223140;
                border-radius: 14px;
                padding: 14px;
                font-size: 14px;
            }}

            QLabel#body {{
                color: #95a4b3;
                font-size: 14px;
                line-height: 1.45;
            }}

            QLabel#miniTitle {{
                color: {TEXT};
                font-size: 14px;
                font-weight: 650;
            }}

            QLabel#pill, QLabel#statusPill {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 13px;
                padding: 8px 12px;
                color: {ACCENT_SOFT};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#statusPill {{
                color: {SUCCESS};
            }}

            QLabel#clock {{
                color: {MUTED};
                font-size: 13px;
                padding-left: 8px;
            }}

            QLabel#sessionStrip {{
                background: #0a1117;
                border: 1px solid #1b2b37;
                border-radius: 12px;
                color: #6f8998;
                padding: 10px 12px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QTextBrowser#conversation {{
                background: transparent;
                border: none;
                color: {TEXT};
                padding: 2px 0;
                font-size: 15px;
            }}

            QLineEdit {{
                background: #0a1017;
                border: 1px solid #223140;
                border-radius: 15px;
                padding: 13px 16px;
                color: {TEXT};
                selection-background-color: #245d68;
                font-size: 15px;
            }}

            QLineEdit:focus {{
                border: 1px solid #4b8f9d;
                background: #0b131b;
            }}

            QPushButton {{
                background: {SURFACE_2};
                border: 1px solid {BORDER};
                border-radius: 13px;
                padding: 10px 15px;
                color: {TEXT};
                font-size: 14px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                border-color: #3d5a70;
                background: #17222d;
            }}

            QPushButton:pressed {{
                background: #1a2b36;
            }}

            QPushButton:disabled {{
                color: #52606d;
                background: #0c1117;
                border-color: #151e27;
            }}

            QPushButton#primaryButton, QPushButton#primaryCompact {{
                background: #163842;
                border-color: #36717c;
                color: {ACCENT_SOFT};
            }}

            QPushButton#primaryButton:hover, QPushButton#primaryCompact:hover {{
                background: #1b4b58;
                border-color: {ACCENT};
            }}

            QPushButton#primaryCompact {{
                padding: 9px 16px;
            }}

            QPushButton#quickButton {{
                background: transparent;
                color: #91a0af;
                padding: 9px 13px;
            }}

            QPushButton#secondaryButton {{
                background: transparent;
                color: #91a0af;
            }}

            QPushButton#iconButton {{
                min-width: 62px;
                background: #0c131b;
            }}

            QFrame#dock {{
                background: #0a0f15;
                border: 1px solid {BORDER_SOFT};
                border-radius: 18px;
            }}

            QPushButton#dockButton, QPushButton#dockActive {{
                min-width: 82px;
                padding: 9px 14px;
                background: transparent;
                border-color: transparent;
                color: #7f8e9d;
            }}

            QPushButton#dockButton:hover {{
                color: {TEXT};
                background: #111923;
                border-color: #1c2a37;
            }}

            QPushButton#dockActive {{
                color: {ACCENT_SOFT};
                background: #111c25;
                border-color: #263b4b;
            }}
            """
        )

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%a, %d %b  ·  %I:%M %p"))

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
                f"<div style='margin:14px 0 14px 80px;'>"
                f"<span style='color:{MUTED}; font-size:11px; font-weight:600;'>YOU</span><br>"
                f"<span style='color:{TEXT}; font-size:15px;'>{safe}</span>"
                f"</div>"
            )
        else:
            block = (
                f"<div style='margin:14px 80px 14px 0;'>"
                f"<span style='color:{ACCENT}; font-size:11px; font-weight:700;'>JARVIS</span><br>"
                f"<span style='color:{TEXT}; font-size:15px;'>{safe}</span>"
                f"</div>"
            )
        self.conversation.append(block)
        bar = self.conversation.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_runtime_status(self, text, state="idle"):
        self.presence_status.setText(str(text).upper())
        self.presence.set_state(state)

    def set_workspace(self, name, details, resumable=True, next_action=None):
        self.workspace_status.setText("RESUMABLE SESSION" if resumable else "CONTEXT AVAILABLE")
        self.workspace_title.setText(str(name))
        self.workspace_meta.setText("\n".join(details) if details else "Context available.")
        self.workspace_next.setText(
            str(next_action) if next_action else "Continue from the latest saved session."
        )
        self.resume_button.setEnabled(bool(resumable))
        self.context_button.setEnabled(True)
        self.continue_action.setEnabled(bool(resumable))
        self.session_strip.setText(
            "SESSION CONTINUITY · READY TO RESUME" if resumable
            else "SESSION CONTINUITY · CONTEXT AVAILABLE"
        )

    def set_workspace_empty(self):
        self.workspace_status.setText("NO SAVED CONTEXT")
        self.workspace_title.setText("No saved workspace yet")
        self.workspace_meta.setText(
            "Open or register a project through JARVIS. The latest work context will live here."
        )
        self.workspace_next.setText("No next action captured yet.")
        self.resume_button.setEnabled(False)
        self.context_button.setEnabled(False)
        self.continue_action.setEnabled(False)
        self.session_strip.setText("SESSION CONTINUITY · WAITING")

    def set_tasks(self, lines):
        self.tasks_label.setText("\n".join(lines) if lines else "No active JARVIS tasks.")

    def set_agents(self, lines):
        self.agents_label.setText("\n".join(lines) if lines else "No agent currently running.")

    def set_approvals(self, lines):
        self.approvals_label.setText("\n".join(lines) if lines else "No pending approvals.")

    def set_today(self, text):
        self.today_label.setText(text or "No active commitments loaded yet.")
