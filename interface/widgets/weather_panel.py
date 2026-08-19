from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class WeatherPanel(QFrame):
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

        title = QLabel("ENVIRONMENT")
        title.setStyleSheet(
            "color:#00eaff;font-size:16px;font-weight:bold;"
        )

        self.info = QLabel(
            "WEATHER\n"
            "────────────\n"
            "NOT CONNECTED\n\n"
            "Location service\n"
            "will be added later."
        )

        self.info.setStyleSheet(
            "color:#b9faff;font-size:13px;"
        )

        layout.addWidget(title)
        layout.addWidget(self.info)