import sys
import subprocess
from datetime import datetime

import psutil

from PySide6.QtCore import (
    Qt,
    QTimer,
    QRectF,
    QPointF,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QFont,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLineEdit,
    QPushButton,
    QProgressBar,
)


# ============================================================
# COLORS
# ============================================================

CYAN = "#00e5ff"
CYAN_DARK = "#006d82"
CYAN_SOFT = "#54f5ff"
BG = "#010509"
PANEL = "rgba(3, 17, 26, 220)"
WHITE = "#dffcff"
MUTED = "#4f98a5"


# ============================================================
# SMALL PANEL
# ============================================================

class HUDPanel(QFrame):

    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.setStyleSheet(f"""
            QFrame {{
                background: {PANEL};
                border: 1px solid {CYAN_DARK};
                border-radius: 10px;
            }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(5)

        self.title = QLabel(title.upper())
        self.title.setStyleSheet(f"""
            color: {CYAN};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 2px;
        """)

        self.layout.addWidget(self.title)


# ============================================================
# GAUGE
# ============================================================

class Gauge(HUDPanel):

    def __init__(self, title, parent=None):
        super().__init__(title, parent)

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(f"""
            color: {WHITE};
            font-size: 22px;
            font-weight: bold;
        """)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)

        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background: #07141b;
                border: none;
                border-radius: 3px;
            }}

            QProgressBar::chunk {{
                background: {CYAN};
                border-radius: 3px;
            }}
        """)

        self.layout.addWidget(self.value_label)
        self.layout.addWidget(self.bar)

    def set_value(self, value):
        value = max(0, min(100, float(value)))

        self.value_label.setText(f"{value:.0f}%")
        self.bar.setValue(int(value))


# ============================================================
# REACTOR
# ============================================================

class Reactor(QWidget):

    def __init__(self):
        super().__init__()

        self.rotation = 0
        self.pulse = 0

        self.setMinimumSize(430, 430)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(25)

    def animate(self):
        self.rotation = (self.rotation + 2) % 360
        self.pulse = (self.pulse + 4) % 360
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()

        # ----------------------------------------------------
        # OUTER ORBIT
        # ----------------------------------------------------

        pen = QPen(QColor(CYAN))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        painter.drawEllipse(
            QRectF(
                center.x() - 175,
                center.y() - 175,
                350,
                350,
            )
        )

        # ----------------------------------------------------
        # SEGMENTED RING
        # ----------------------------------------------------

        pen.setWidth(4)
        painter.setPen(pen)

        painter.drawArc(
            QRectF(
                center.x() - 155,
                center.y() - 155,
                310,
                310,
            ),
            self.rotation * 16,
            80 * 16,
        )

        painter.drawArc(
            QRectF(
                center.x() - 155,
                center.y() - 155,
                310,
                310,
            ),
            (self.rotation + 180) * 16,
            55 * 16,
        )

        # ----------------------------------------------------
        # INNER RING
        # ----------------------------------------------------

        pen.setWidth(2)
        pen.setColor(QColor("#008db0"))

        painter.setPen(pen)

        painter.drawEllipse(
            QRectF(
                center.x() - 120,
                center.y() - 120,
                240,
                240,
            )
        )

        painter.drawArc(
            QRectF(
                center.x() - 115,
                center.y() - 115,
                230,
                230,
            ),
            -self.rotation * 12,
            100 * 16,
        )

        # ----------------------------------------------------
        # RADIAL MARKERS
        # ----------------------------------------------------

        painter.setPen(
            QPen(QColor(CYAN_DARK), 2)
        )

        import math

        for i in range(24):

            angle = math.radians(
                i * 15
            )

            r1 = 182
            r2 = 190

            x1 = center.x() + math.cos(angle) * r1
            y1 = center.y() + math.sin(angle) * r1

            x2 = center.x() + math.cos(angle) * r2
            y2 = center.y() + math.sin(angle) * r2

            painter.drawLine(
                QPointF(x1, y1),
                QPointF(x2, y2),
            )

        # ----------------------------------------------------
        # CORE GLOW
        # ----------------------------------------------------

        glow = 39 + int(
            abs(
                (self.pulse % 180) - 90
            ) / 8
        )

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QBrush(QColor("#0088ff"))
        )

        painter.drawEllipse(
            QRectF(
                center.x() - glow,
                center.y() - glow,
                glow * 2,
                glow * 2,
            )
        )

        painter.setBrush(
            QBrush(QColor("#d8fbff"))
        )

        painter.drawEllipse(
            QRectF(
                center.x() - 17,
                center.y() - 17,
                34,
                34,
            )
        )

        # ----------------------------------------------------
        # CENTER TEXT
        # ----------------------------------------------------

        painter.setPen(
            QColor("#8dfaff")
        )

        font = QFont("Segoe UI")
        font.setPointSize(9)
        font.setBold(True)

        painter.setFont(font)

        text_rect = QRectF(
            center.x() - 100,
            center.y() + 58,
            200,
            25,
        )

        painter.drawText(
            text_rect,
            Qt.AlignCenter,
            "J A R V I S   C O R E",
        )


# ============================================================
# ACTIVITY GRAPH
# ============================================================

class ActivityGraph(QFrame):

    def __init__(self, title):
        super().__init__()

        self.values = [15] * 60

        self.setStyleSheet(f"""
            QFrame {{
                background: {PANEL};
                border: 1px solid {CYAN_DARK};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        title_label = QLabel(title.upper())

        title_label.setStyleSheet(f"""
            color: {CYAN};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 2px;
        """)

        layout.addWidget(title_label)

        self.canvas = GraphCanvas(self.values)
        layout.addWidget(self.canvas)

    def push(self, value):

        self.values.append(
            max(0, min(100, value))
        )

        if len(self.values) > 60:
            self.values.pop(0)

        self.canvas.values = self.values
        self.canvas.update()


class GraphCanvas(QWidget):

    def __init__(self, values):
        super().__init__()

        self.values = values

        self.setMinimumHeight(55)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.values:
            return

        w = self.width()
        h = self.height()

        pen = QPen(
            QColor(CYAN),
            2
        )

        painter.setPen(pen)

        last = None

        for i, value in enumerate(self.values):

            x = (
                i
                / max(1, len(self.values) - 1)
                * w
            )

            y = h - (
                value / 100 * h
            )

            point = QPointF(x, y)

            if last:
                painter.drawLine(
                    last,
                    point
                )

            last = point


# ============================================================
# TEXT PANEL
# ============================================================

class InfoPanel(HUDPanel):

    def __init__(self, title, lines=None):
        super().__init__(title)

        self.info = QLabel()

        self.info.setStyleSheet(f"""
            color: {WHITE};
            font-size: 12px;
        """)

        self.layout.addWidget(
            self.info
        )

        self.set_lines(
            lines or []
        )

    def set_lines(self, lines):

        self.info.setText(
            "\n".join(lines)
        )


# ============================================================
# MAIN HUD
# ============================================================

class JarvisHUD(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "JARVIS OS"
        )

        self.showFullScreen()

        self.setStyleSheet("""
            QWidget {
                background: #010509;
                color: white;
                font-family: Segoe UI;
            }

            QLineEdit {
                background: rgba(2, 17, 25, 235);
                border: 1px solid #00d9ff;
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-size: 14px;
            }

            QPushButton {
                background: rgba(0, 74, 95, 220);
                border: 1px solid #00d9ff;
                border-radius: 8px;
                padding: 11px 18px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background: rgba(0, 150, 190, 220);
            }
        """)

        self.cpu_history = []
        self.net_history = []

        self.build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self.update_all
        )
        self.timer.start(1000)

        self.update_all()

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            16, 12, 16, 12
        )

        root.setSpacing(10)

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = QHBoxLayout()

        logo = QLabel(
            "J A R V I S"
        )

        logo.setStyleSheet(f"""
            color: {CYAN};
            font-size: 30px;
            font-weight: bold;
            letter-spacing: 8px;
        """)

        self.time_label = QLabel()

        self.time_label.setStyleSheet(f"""
            color: {CYAN_SOFT};
            font-size: 18px;
        """)

        self.time_label.setAlignment(
            Qt.AlignRight
        )

        header.addWidget(logo)
        header.addStretch()
        header.addWidget(
            self.time_label
        )

        root.addLayout(header)

        # ----------------------------------------------------
        # TOP TELEMETRY
        # ----------------------------------------------------

        telemetry = QHBoxLayout()

        self.cpu = Gauge("CPU")
        self.ram = Gauge("RAM")
        self.disk = Gauge("STORAGE")

        self.gpu = InfoPanel(
            "GPU",
            [
                "RTX 5060",
                "STATUS     ONLINE",
                "VRAM       --",
            ]
        )

        telemetry.addWidget(self.cpu, 1)
        telemetry.addWidget(self.ram, 1)
        telemetry.addWidget(self.disk, 1)
        telemetry.addWidget(self.gpu, 1)

        root.addLayout(telemetry)

        # ----------------------------------------------------
        # MAIN AREA
        # ----------------------------------------------------

        main = QHBoxLayout()

        # LEFT
        left = QVBoxLayout()

        self.storage_info = InfoPanel(
            "STORAGE",
            [
                "LOCAL DISK",
                "STATUS     ONLINE",
                "FREE       --",
            ]
        )

        self.activity = ActivityGraph(
            "SYSTEM ACTIVITY"
        )

        left.addWidget(
            self.storage_info
        )

        left.addWidget(
            self.activity,
            1
        )

        # CENTER
        center = QVBoxLayout()

        core_label = QLabel(
            "CORE • ONLINE"
        )

        core_label.setAlignment(
            Qt.AlignCenter
        )

        core_label.setStyleSheet(f"""
            color: {CYAN};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 5px;
        """)

        self.reactor = Reactor()

        center.addWidget(
            core_label
        )

        center.addWidget(
            self.reactor,
            alignment=Qt.AlignCenter
        )

        self.status = QLabel(
            "SYSTEM READY"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        self.status.setStyleSheet(f"""
            color: {MUTED};
            font-size: 10px;
            letter-spacing: 3px;
        """)

        center.addWidget(
            self.status
        )

        # RIGHT
        right = QVBoxLayout()

        self.network = InfoPanel(
            "NETWORK",
            [
                "STATUS     ONLINE",
                "DOWNLOAD   -- KB/s",
                "UPLOAD     -- KB/s",
            ]
        )

        self.environment = InfoPanel(
            "ENVIRONMENT",
            [
                "WEATHER    OFFLINE",
                "LOCATION   NOT SET",
                "SERVICE    STANDBY",
            ]
        )

        right.addWidget(
            self.network
        )

        right.addWidget(
            self.environment
        )

        # ADD
        main.addLayout(left, 1)
        main.addLayout(center, 2)
        main.addLayout(right, 1)

        root.addLayout(main, 1)

        # ----------------------------------------------------
        # LOWER SECTION
        # ----------------------------------------------------

        lower = QHBoxLayout()

        self.apps = InfoPanel(
            "APPLICATIONS",
            [
                "● VS CODE",
                "● CHROME",
                "● DISCORD",
                "● TERMINAL",
            ]
        )

        self.events = ActivityGraph(
            "NETWORK ACTIVITY"
        )

        self.media = InfoPanel(
            "MEDIA",
            [
                "PLAYER     IDLE",
                "TRACK      --",
                "VOLUME     --",
            ]
        )

        lower.addWidget(
            self.apps,
            1
        )

        lower.addWidget(
            self.events,
            1
        )

        lower.addWidget(
            self.media,
            1
        )

        root.addLayout(lower)

        # ----------------------------------------------------
        # COMMAND AREA
        # ----------------------------------------------------

        command = QHBoxLayout()

        self.input = QLineEdit()

        self.input.setPlaceholderText(
            "Talk to JARVIS..."
        )

        listen = QPushButton(
            "🎤 LISTEN"
        )

        execute = QPushButton(
            "EXECUTE"
        )

        command.addWidget(
            self.input
        )

        command.addWidget(
            listen
        )

        command.addWidget(
            execute
        )

        root.addLayout(command)

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        footer = QLabel(
            "JARVIS OS  •  LOCAL AI  •  TOOLS  •  MEMORY  •  VOICE"
        )

        footer.setAlignment(
            Qt.AlignCenter
        )

        footer.setStyleSheet(f"""
            color: {CYAN_DARK};
            font-size: 9px;
            letter-spacing: 3px;
        """)

        root.addWidget(
            footer
        )

        execute.clicked.connect(
            self.execute_command
        )

    # ========================================================
    # TELEMETRY
    # ========================================================

    def update_all(self):

        now = datetime.now()

        self.time_label.setText(
            now.strftime(
                "%A  •  %d %B  •  %I:%M:%S %p"
            )
        )

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        self.cpu.set_value(cpu)
        self.ram.set_value(ram)
        self.disk.set_value(disk)

        self.activity.push(
            cpu
        )

        # ----------------------------------------------------
        # STORAGE
        # ----------------------------------------------------

        drive = psutil.disk_usage("/")

        free_gb = (
            drive.free
            / (1024 ** 3)
        )

        self.storage_info.set_lines([
            "LOCAL DISK",
            f"USED       {drive.percent:.0f}%",
            f"FREE       {free_gb:.1f} GB",
            "STATUS     ONLINE",
        ])

        # ----------------------------------------------------
        # NETWORK
        # ----------------------------------------------------

        net = psutil.net_io_counters()

        if not hasattr(
            self,
            "previous_net"
        ):
            self.previous_net = net
            return

        down = max(
            0,
            net.bytes_recv
            - self.previous_net.bytes_recv
        )

        up = max(
            0,
            net.bytes_sent
            - self.previous_net.bytes_sent
        )

        self.previous_net = net

        down_kb = down / 1024
        up_kb = up / 1024

        self.network.set_lines([
            "STATUS     ONLINE",
            f"DOWNLOAD   {down_kb:.1f} KB/s",
            f"UPLOAD     {up_kb:.1f} KB/s",
        ])

        self.events.push(
            min(
                100,
                down_kb / 20
            )
        )

        # ----------------------------------------------------
        # GPU
        # ----------------------------------------------------

        self.update_gpu()

    # ========================================================
    # GPU
    # ========================================================

    def update_gpu(self):

        try:

            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=1,
            )

            if result.returncode != 0:
                return

            parts = [
                p.strip()
                for p in result.stdout.strip().split(",")
            ]

            if len(parts) >= 4:

                utilization = parts[0]
                used = parts[1]
                total = parts[2]
                temp = parts[3]

                self.gpu.set_lines([
                    "RTX 5060",
                    f"GPU        {utilization}%",
                    f"VRAM       {used}/{total} MB",
                    f"TEMP       {temp}°C",
                ])

        except Exception:
            pass

    # ========================================================
    # COMMAND
    # ========================================================

    def execute_command(self):

        command = self.input.text().strip()

        if not command:
            return

        print(
            f"JARVIS COMMAND: {command}"
        )

        self.status.setText(
            "PROCESSING"
        )

        self.input.clear()


# ============================================================
# APP
# ============================================================

def main():

    app = QApplication(sys.argv)

    window = JarvisHUD()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()