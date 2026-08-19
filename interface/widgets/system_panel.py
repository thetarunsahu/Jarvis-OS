import psutil

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class SystemPanel(QFrame):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QFrame {
                background: rgba(3, 18, 28, 220);
                border: 1px solid #007f9f;
                border-radius: 14px;
            }
        """)

        layout = QVBoxLayout(self)

        self.title = QLabel("SYSTEM")
        self.title.setStyleSheet(
            "color:#00eaff;font-size:16px;font-weight:bold;"
        )

        self.info = QLabel()
        self.info.setStyleSheet(
            "color:#b9faff;font-size:13px;line-height:1.5;"
        )

        layout.addWidget(self.title)
        layout.addWidget(self.info)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.update_stats()

    def update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent

        self.info.setText(
            f"CPU        {cpu:5.1f}%\n"
            f"RAM        {ram:5.1f}%\n"
            f"DISK       {disk:5.1f}%\n"
            f"MEMORY     ONLINE\n"
            f"TOOLS      READY\n"
            f"CORE       ONLINE"
        )