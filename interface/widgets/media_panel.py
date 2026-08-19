from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class MediaPanel(QFrame):
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

        title = QLabel("MEDIA")
        title.setStyleSheet(
            "color:#00eaff;font-size:16px;font-weight:bold;"
        )

        self.info = QLabel(
            "PLAYER\n"
            "────────────\n"
            "NO MEDIA ACTIVE"
        )

        self.info.setStyleSheet(
            "color:#b9faff;font-size:13px;"
        )

        layout.addWidget(title)
        layout.addWidget(self.info)