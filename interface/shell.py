import html
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from interface.home import PresenceCore


BG = "#070a0f"
SURFACE = "#0d141c"
SURFACE_ALT = "#0a1017"
BORDER = "#1d2a38"
TEXT = "#f3f7fa"
MUTED = "#8392a2"
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


class PageHeader(QWidget):
    def __init__(self, eyebrow, title, body, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        top = QLabel(eyebrow.upper())
        top.setObjectName("accentEyebrow")
        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        heading.setWordWrap(True)
        copy = QLabel(body)
        copy.setObjectName("pageBody")
        copy.setWordWrap(True)

        layout.addWidget(top)
        layout.addWidget(heading)
        layout.addWidget(copy)


class JarvisShell(QWidget):
    """Primary multi-page AI operating environment shell.

    Home stays conversational. Workspace, Files and Tasks are actual product
    surfaces instead of commands that dump diagnostic text into the chat.
    """

    command_submitted = Signal(str)
    diagnostics_requested = Signal()
    workspace_resume_requested = Signal()
    file_search_requested = Signal(str)
    file_reindex_requested = Signal()

    PAGE_HOME = 0
    PAGE_WORKSPACE = 1
    PAGE_FILES = 2
    PAGE_TASKS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS")
        self.setMinimumSize(1180, 720)
        self.nav_buttons = {}
        self._build_ui()
        self._apply_style()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        root.addLayout(self._build_header())

        self.pages = QStackedWidget()
        self.pages.setObjectName("pages")
        self.pages.addWidget(self._build_home_page())
        self.pages.addWidget(self._build_workspace_page())
        self.pages.addWidget(self._build_files_page())
        self.pages.addWidget(self._build_tasks_page())
        root.addWidget(self.pages, 1)

        # Persistent command interface: JARVIS remains available on every page.
        command_surface = QFrame()
        command_surface.setObjectName("commandBar")
        command_row = QHBoxLayout(command_surface)
        command_row.setContentsMargins(12, 8, 8, 8)
        command_row.setSpacing(9)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask JARVIS or do anything...")
        self.input.setMinimumHeight(46)
        self.input.returnPressed.connect(self._submit_command)

        self.listen_button = QPushButton("Voice")
        self.listen_button.setObjectName("secondaryButton")
        self.listen_button.setMinimumHeight(46)
        self.listen_button.setMinimumWidth(78)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("primaryButton")
        self.send_button.setMinimumHeight(46)
        self.send_button.clicked.connect(self._submit_command)

        command_row.addWidget(self.input, 1)
        command_row.addWidget(self.listen_button)
        command_row.addWidget(self.send_button)
        root.addWidget(command_surface)

        root.addWidget(self._build_dock())
        self.show_page(self.PAGE_HOME)

    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        brand = QVBoxLayout()
        brand.setSpacing(1)
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

        row.addLayout(brand)
        row.addStretch()
        row.addWidget(self.model_label)
        row.addWidget(self.status_label)
        row.addWidget(self.clock_label)
        return row

    def _build_home_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        center = QVBoxLayout()
        center.setSpacing(16)

        hero = Surface()
        hero.setObjectName("heroSurface")
        hero.setMinimumHeight(250)
        hero.setMaximumHeight(310)
        hero_row = QHBoxLayout()
        hero_row.setSpacing(18)

        copy = QVBoxLayout()
        copy.setSpacing(8)
        copy.addStretch()
        eyebrow = QLabel("JARVIS CORE")
        eyebrow.setObjectName("accentEyebrow")
        self.greeting = QLabel("Ready when you are.")
        self.greeting.setObjectName("heroTitle")
        self.greeting.setWordWrap(True)
        body = QLabel("Continue where you stopped, ask naturally, or delegate a new goal.")
        body.setObjectName("heroBody")
        body.setWordWrap(True)
        self.presence_status = QLabel("SYSTEM READY")
        self.presence_status.setObjectName("presenceStatus")

        copy.addWidget(eyebrow)
        copy.addWidget(self.greeting)
        copy.addWidget(body)
        copy.addWidget(self.presence_status)

        quick = QHBoxLayout()
        quick.setSpacing(8)
        self.continue_action = QPushButton("Continue work")
        self.continue_action.setObjectName("primaryCompact")
        self.continue_action.setEnabled(False)
        self.continue_action.clicked.connect(self.workspace_resume_requested.emit)

        workspace_quick = QPushButton("Workspace")
        workspace_quick.setObjectName("quietButton")
        workspace_quick.clicked.connect(lambda: self.show_page(self.PAGE_WORKSPACE))
        files_quick = QPushButton("Files")
        files_quick.setObjectName("quietButton")
        files_quick.clicked.connect(lambda: self.show_page(self.PAGE_FILES))
        tasks_quick = QPushButton("Tasks")
        tasks_quick.setObjectName("quietButton")
        tasks_quick.clicked.connect(lambda: self.show_page(self.PAGE_TASKS))

        quick.addWidget(self.continue_action)
        quick.addWidget(workspace_quick)
        quick.addWidget(files_quick)
        quick.addWidget(tasks_quick)
        quick.addStretch()
        copy.addLayout(quick)
        copy.addStretch()

        self.presence = PresenceCore()
        self.presence.setMinimumSize(210, 210)
        self.presence.setMaximumSize(250, 250)
        hero_row.addLayout(copy, 1)
        hero_row.addWidget(self.presence, 0, Qt.AlignCenter)
        hero.layout.addLayout(hero_row)
        center.addWidget(hero)

        conversation_surface = Surface("CONVERSATION")
        conversation_surface.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.conversation = QTextBrowser()
        self.conversation.setObjectName("conversation")
        self.conversation.setOpenExternalLinks(True)
        conversation_surface.layout.addWidget(self.conversation, 1)
        self.append_message(
            "jarvis",
            "I am ready. Talk to me normally; workspace, files and tasks now have their own views.",
        )
        center.addWidget(conversation_surface, 1)

        side = QVBoxLayout()
        side.setSpacing(16)

        current = Surface("CURRENT WORK")
        current.setMinimumWidth(300)
        current.setMaximumWidth(360)
        self.workspace_status = QLabel("NO SAVED CONTEXT")
        self.workspace_status.setObjectName("workspaceStatus")
        self.workspace_title = QLabel("No saved workspace")
        self.workspace_title.setObjectName("workspaceTitle")
        self.workspace_title.setWordWrap(True)
        self.workspace_meta = QLabel("Your latest project context will appear here.")
        self.workspace_meta.setObjectName("body")
        self.workspace_meta.setWordWrap(True)
        self.workspace_next = QLabel("No next action captured yet.")
        self.workspace_next.setObjectName("callout")
        self.workspace_next.setWordWrap(True)

        self.resume_button = QPushButton("Continue workspace")
        self.resume_button.setObjectName("primaryButton")
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.workspace_resume_requested.emit)
        self.context_button = QPushButton("Open workspace view")
        self.context_button.setObjectName("secondaryButton")
        self.context_button.clicked.connect(lambda: self.show_page(self.PAGE_WORKSPACE))

        current.layout.addWidget(self.workspace_status)
        current.layout.addWidget(self.workspace_title)
        current.layout.addWidget(self.workspace_meta)
        current.layout.addWidget(self.workspace_next)
        current.layout.addStretch()
        current.layout.addWidget(self.resume_button)
        current.layout.addWidget(self.context_button)

        today = Surface("TODAY")
        self.today_label = QLabel("No active commitments loaded yet.")
        self.today_label.setObjectName("body")
        self.today_label.setWordWrap(True)
        today.layout.addWidget(self.today_label)

        live = Surface("LIVE ACTIVITY")
        self.tasks_label = QLabel("No active JARVIS tasks.")
        self.tasks_label.setObjectName("body")
        self.tasks_label.setWordWrap(True)
        self.agents_label = QLabel("No agent currently running.")
        self.agents_label.setObjectName("body")
        self.agents_label.setWordWrap(True)
        live.layout.addWidget(self.tasks_label)
        live.layout.addWidget(self.agents_label)

        side.addWidget(current, 2)
        side.addWidget(today)
        side.addWidget(live)
        side.addStretch()

        layout.addLayout(center, 1)
        layout.addLayout(side)
        return page

    def _build_workspace_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(
            PageHeader(
                "Session continuity",
                "Workspace",
                "See where you stopped, what changed, and resume the project without digging through applications.",
            )
        )

        columns = QHBoxLayout()
        columns.setSpacing(16)

        overview = Surface("PROJECT CONTEXT")
        self.workspace_page_status = QLabel("NO SAVED CONTEXT")
        self.workspace_page_status.setObjectName("workspaceStatus")
        self.workspace_page_title = QLabel("No workspace loaded")
        self.workspace_page_title.setObjectName("pageCardTitle")
        self.workspace_page_title.setWordWrap(True)
        self.workspace_page_details = QLabel("Project context has not been captured yet.")
        self.workspace_page_details.setObjectName("body")
        self.workspace_page_details.setWordWrap(True)
        self.workspace_page_next = QLabel("No next action captured yet.")
        self.workspace_page_next.setObjectName("largeCallout")
        self.workspace_page_next.setWordWrap(True)
        overview.layout.addWidget(self.workspace_page_status)
        overview.layout.addWidget(self.workspace_page_title)
        overview.layout.addWidget(self.workspace_page_details)
        overview.layout.addSpacing(10)
        overview.layout.addWidget(QLabel("NEXT ACTION", objectName="sectionTitle"))
        overview.layout.addWidget(self.workspace_page_next)
        overview.layout.addStretch()

        actions = Surface("RESUME PACKAGE")
        actions.setMinimumWidth(330)
        actions.setMaximumWidth(410)
        self.session_strip = QLabel("SESSION CONTINUITY · WAITING")
        self.session_strip.setObjectName("sessionStrip")
        self.session_strip.setWordWrap(True)
        self.workspace_resume_hint = QLabel(
            "JARVIS will restore the registered project in its preferred application and reopen captured files when available."
        )
        self.workspace_resume_hint.setObjectName("body")
        self.workspace_resume_hint.setWordWrap(True)
        self.workspace_page_resume = QPushButton("Resume in VS Code")
        self.workspace_page_resume.setObjectName("primaryButton")
        self.workspace_page_resume.setMinimumHeight(50)
        self.workspace_page_resume.setEnabled(False)
        self.workspace_page_resume.clicked.connect(self.workspace_resume_requested.emit)
        actions.layout.addWidget(self.session_strip)
        actions.layout.addWidget(self.workspace_resume_hint)
        actions.layout.addStretch()
        actions.layout.addWidget(self.workspace_page_resume)

        columns.addWidget(overview, 1)
        columns.addWidget(actions)
        root.addLayout(columns, 1)
        return page

    def _build_files_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(
            PageHeader(
                "File intelligence",
                "Find work by meaning, not by path",
                "Search the JARVIS file index without remembering exact folders or filenames.",
            )
        )

        search_surface = Surface("SEARCH")
        search_row = QHBoxLayout()
        search_row.setSpacing(9)
        self.file_search_input = QLineEdit()
        self.file_search_input.setPlaceholderText("e.g. architecture, YOLO, robotics report...")
        self.file_search_input.setMinimumHeight(46)
        self.file_search_input.returnPressed.connect(self._submit_file_search)
        search_button = QPushButton("Search")
        search_button.setObjectName("primaryButton")
        search_button.clicked.connect(self._submit_file_search)
        self.file_reindex_button = QPushButton("Refresh index")
        self.file_reindex_button.setObjectName("secondaryButton")
        self.file_reindex_button.clicked.connect(self.file_reindex_requested.emit)
        search_row.addWidget(self.file_search_input, 1)
        search_row.addWidget(search_button)
        search_row.addWidget(self.file_reindex_button)
        search_surface.layout.addLayout(search_row)

        self.file_status_label = QLabel("Index status has not been loaded yet.")
        self.file_status_label.setObjectName("body")
        self.file_status_label.setWordWrap(True)
        search_surface.layout.addWidget(self.file_status_label)
        root.addWidget(search_surface)

        results = Surface("RESULTS")
        self.file_result_title = QLabel("Search for a file or concept.")
        self.file_result_title.setObjectName("pageCardTitle")
        self.file_results = QListWidget()
        self.file_results.setObjectName("resultList")
        self.file_results.setSpacing(4)
        results.layout.addWidget(self.file_result_title)
        results.layout.addWidget(self.file_results, 1)
        root.addWidget(results, 1)
        return page

    def _build_tasks_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        root.addWidget(
            PageHeader(
                "Agent runtime",
                "Tasks & Agents",
                "See what JARVIS is doing, what finished, what failed, and what still needs approval.",
            )
        )

        columns = QHBoxLayout()
        columns.setSpacing(16)

        work = Surface("RECENT TASKS")
        self.task_page_label = QLabel("No JARVIS tasks recorded yet.")
        self.task_page_label.setObjectName("body")
        self.task_page_label.setWordWrap(True)
        work.layout.addWidget(self.task_page_label)
        work.layout.addStretch()

        runtime = Surface("RUNTIME")
        runtime.setMinimumWidth(330)
        runtime.setMaximumWidth(420)
        agent_title = QLabel("AGENTS")
        agent_title.setObjectName("sectionTitle")
        self.task_agents_label = QLabel("No agent currently running.")
        self.task_agents_label.setObjectName("body")
        self.task_agents_label.setWordWrap(True)
        approval_title = QLabel("APPROVALS")
        approval_title.setObjectName("sectionTitle")
        self.approvals_label = QLabel("No pending approvals.")
        self.approvals_label.setObjectName("body")
        self.approvals_label.setWordWrap(True)
        runtime.layout.addWidget(agent_title)
        runtime.layout.addWidget(self.task_agents_label)
        runtime.layout.addSpacing(16)
        runtime.layout.addWidget(approval_title)
        runtime.layout.addWidget(self.approvals_label)
        runtime.layout.addStretch()

        columns.addWidget(work, 1)
        columns.addWidget(runtime)
        root.addLayout(columns, 1)
        return page

    def _build_dock(self):
        dock = QFrame()
        dock.setObjectName("dock")
        row = QHBoxLayout(dock)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(6)
        row.addStretch()

        for name, page_index in (
            ("Home", self.PAGE_HOME),
            ("Workspace", self.PAGE_WORKSPACE),
            ("Files", self.PAGE_FILES),
            ("Tasks", self.PAGE_TASKS),
        ):
            button = QPushButton(name)
            button.clicked.connect(lambda checked=False, index=page_index: self.show_page(index))
            self.nav_buttons[page_index] = button
            row.addWidget(button)

        diagnostics = QPushButton("Diagnostics")
        diagnostics.setObjectName("dockButton")
        diagnostics.clicked.connect(self.diagnostics_requested.emit)
        row.addWidget(diagnostics)
        row.addStretch()
        return dock

    def show_page(self, index):
        index = max(0, min(self.pages.count() - 1, int(index)))
        self.pages.setCurrentIndex(index)
        for page_index, button in self.nav_buttons.items():
            button.setObjectName("dockActive" if page_index == index else "dockButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _submit_command(self):
        command = self.input.text().strip()
        if not command:
            return
        self.input.clear()
        self.show_page(self.PAGE_HOME)
        self.append_message("you", command)
        self.command_submitted.emit(command)

    def _submit_file_search(self):
        query = self.file_search_input.text().strip()
        if query:
            self.file_search_requested.emit(query)

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%a, %d %b  ·  %I:%M %p"))

    def append_message(self, role, text):
        safe = html.escape(str(text)).replace("\n", "<br>")
        if role == "you":
            block = (
                f"<div style='margin:14px 0 14px 72px;'>"
                f"<span style='color:{MUTED}; font-size:11px; font-weight:600;'>YOU</span><br>"
                f"<span style='color:{TEXT}; font-size:15px;'>{safe}</span></div>"
            )
        else:
            block = (
                f"<div style='margin:14px 72px 14px 0;'>"
                f"<span style='color:{ACCENT}; font-size:11px; font-weight:700;'>JARVIS</span><br>"
                f"<span style='color:{TEXT}; font-size:15px;'>{safe}</span></div>"
            )
        self.conversation.append(block)
        bar = self.conversation.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_runtime_status(self, text, state="idle"):
        self.presence_status.setText(str(text).upper())
        self.presence.set_state(state)

    def set_workspace(self, name, details, resumable=True, next_action=None):
        detail_text = "\n".join(details) if details else "Context available."
        next_text = str(next_action) if next_action else "Continue from the latest saved session."
        status = "RESUMABLE SESSION" if resumable else "CONTEXT AVAILABLE"

        self.workspace_status.setText(status)
        self.workspace_title.setText(str(name))
        self.workspace_meta.setText(detail_text)
        self.workspace_next.setText(next_text)
        self.resume_button.setEnabled(bool(resumable))
        self.continue_action.setEnabled(bool(resumable))

        self.workspace_page_status.setText(status)
        self.workspace_page_title.setText(str(name))
        self.workspace_page_details.setText(detail_text)
        self.workspace_page_next.setText(next_text)
        self.workspace_page_resume.setEnabled(bool(resumable))

        self.session_strip.setText(
            "SESSION CONTINUITY · READY TO RESUME" if resumable
            else "SESSION CONTINUITY · CONTEXT AVAILABLE"
        )

    def set_workspace_empty(self):
        self.workspace_status.setText("NO SAVED CONTEXT")
        self.workspace_title.setText("No saved workspace")
        self.workspace_meta.setText("Your latest project context will appear here.")
        self.workspace_next.setText("No next action captured yet.")
        self.resume_button.setEnabled(False)
        self.continue_action.setEnabled(False)
        self.workspace_page_status.setText("NO SAVED CONTEXT")
        self.workspace_page_title.setText("No workspace loaded")
        self.workspace_page_details.setText("Project context has not been captured yet.")
        self.workspace_page_next.setText("No next action captured yet.")
        self.workspace_page_resume.setEnabled(False)
        self.session_strip.setText("SESSION CONTINUITY · WAITING")

    def set_tasks(self, lines):
        text = "\n".join(lines) if lines else "No active JARVIS tasks."
        self.tasks_label.setText(text)
        self.task_page_label.setText(text)

    def set_agents(self, lines):
        text = "\n".join(lines) if lines else "No agent currently running."
        self.agents_label.setText(text)
        self.task_agents_label.setText(text)

    def set_approvals(self, lines):
        self.approvals_label.setText("\n".join(lines) if lines else "No pending approvals.")

    def set_today(self, text):
        self.today_label.setText(text or "No active commitments loaded yet.")

    def set_file_status(self, status):
        status = status or {}
        roots = status.get("roots") or []
        semantic = "on" if status.get("semantic") else "off"
        fts = "enabled" if status.get("fts") else "fallback"
        root_text = roots[0] if roots else "No roots configured"
        self.file_status_label.setText(
            f"{status.get('files', 0)} indexed files  ·  FTS {fts}  ·  semantic {semantic}\n{root_text}"
        )

    def set_file_indexing(self, active):
        self.file_reindex_button.setEnabled(not active)
        self.file_reindex_button.setText("Indexing…" if active else "Refresh index")

    def set_file_results(self, query, matches):
        matches = matches or []
        self.file_results.clear()
        self.file_result_title.setText(
            f"{len(matches)} result(s) for “{query}”" if matches
            else f"No indexed files matched “{query}”."
        )
        for match in matches:
            name = str(match.get("name") or "Unnamed file")
            path = str(match.get("path") or "")
            extension = str(match.get("extension") or "")
            item = QListWidgetItem(f"{name}\n{path}")
            if extension:
                item.setToolTip(f"{extension} · {path}")
            item.setData(Qt.UserRole, path)
            self.file_results.addItem(item)

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QWidget {{
                background: {BG};
                color: {TEXT};
                font-family: 'Segoe UI';
                font-size: 15px;
            }}
            QFrame#surface, QFrame#heroSurface {{
                background: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 18px;
            }}
            QFrame#heroSurface {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #101923,stop:1 #0b1118);
                border-color: #233445;
            }}
            QLabel#brand {{ font-size: 28px; font-weight: 700; letter-spacing: 6px; }}
            QLabel#eyebrow, QLabel#sectionTitle {{ color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
            QLabel#accentEyebrow {{ color: {ACCENT}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
            QLabel#heroTitle {{ font-size: 34px; font-weight: 650; }}
            QLabel#heroBody, QLabel#pageBody, QLabel#body {{ color: #96a5b5; font-size: 14px; }}
            QLabel#pageTitle {{ font-size: 30px; font-weight: 650; }}
            QLabel#pageCardTitle, QLabel#workspaceTitle {{ font-size: 23px; font-weight: 650; }}
            QLabel#workspaceStatus {{ color: {SUCCESS}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
            QLabel#presenceStatus {{ color: {ACCENT_SOFT}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
            QLabel#callout, QLabel#largeCallout, QLabel#sessionStrip {{
                background: {SURFACE_ALT}; border: 1px solid #223140; border-radius: 13px; padding: 13px;
            }}
            QLabel#largeCallout {{ font-size: 17px; color: {TEXT}; }}
            QLabel#sessionStrip {{ color: #7e9baa; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#pill, QLabel#statusPill {{
                background: #111a24; border: 1px solid {BORDER}; border-radius: 12px; padding: 8px 11px;
                color: {ACCENT_SOFT}; font-size: 11px; font-weight: 700;
            }}
            QLabel#statusPill {{ color: {SUCCESS}; }}
            QLabel#clock {{ color: {MUTED}; font-size: 12px; padding-left: 6px; }}
            QTextBrowser#conversation {{ background: transparent; border: none; padding: 2px; }}
            QLineEdit {{
                background: {SURFACE_ALT}; border: 1px solid #223140; border-radius: 13px;
                padding: 11px 14px; color: {TEXT}; font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: #4b8f9d; }}
            QPushButton {{
                background: #111a24; border: 1px solid {BORDER}; border-radius: 12px;
                padding: 9px 14px; color: {TEXT}; font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #17222d; border-color: #3d5a70; }}
            QPushButton:disabled {{ color: #52606d; background: #0c1117; border-color: #151e27; }}
            QPushButton#primaryButton, QPushButton#primaryCompact {{ background: #163842; border-color: #36717c; color: {ACCENT_SOFT}; }}
            QPushButton#primaryButton:hover, QPushButton#primaryCompact:hover {{ background: #1b4b58; border-color: {ACCENT}; }}
            QPushButton#secondaryButton, QPushButton#quietButton {{ background: transparent; color: #91a0af; }}
            QFrame#commandBar, QFrame#dock {{ background: #0a0f15; border: 1px solid #15202b; border-radius: 16px; }}
            QPushButton#dockButton, QPushButton#dockActive {{ min-width: 86px; background: transparent; border-color: transparent; color: #7f8e9d; }}
            QPushButton#dockButton:hover {{ color: {TEXT}; background: #111923; border-color: #1c2a37; }}
            QPushButton#dockActive {{ color: {ACCENT_SOFT}; background: #111c25; border-color: #263b4b; }}
            QListWidget#resultList {{
                background: transparent; border: none; outline: none; color: {TEXT};
            }}
            QListWidget#resultList::item {{
                background: {SURFACE_ALT}; border: 1px solid #1d2a38; border-radius: 12px;
                padding: 12px; margin: 2px 0;
            }}
            QListWidget#resultList::item:selected {{ background: #163842; border-color: #36717c; }}
            """
        )
