import psutil

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class NetworkPanel(QFrame):
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

        title = QLabel("NETWORK")
        title.setStyleSheet(
            "color:#00eaff;font-size:16px;font-weight:bold;"
        )

        self.info = QLabel()
        self.info.setStyleSheet(
            "color:#b9faff;font-size:13px;"
        )

        layout.addWidget(title)
        layout.addWidget(self.info)

        self.old = psutil.net_io_counters()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_network)
        self.timer.start(1000)

        self.update_network()

    def update_network(self):
        current = psutil.net_io_counters()

        down = max(
            0,
            current.bytes_recv - self.old.bytes_recv
        )

        up = max(
            0,
            current.bytes_sent - self.old.bytes_sent
        )

        self.old = current

        down_kb = down / 1024
        up_kb = up / 1024

        self.info.setText(
            f"DOWNLOAD   {down_kb:7.1f} KB/s\n"
            f"UPLOAD     {up_kb:7.1f} KB/s\n"
            f"STATUS     ONLINE"
        )