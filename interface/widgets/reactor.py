from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class Reactor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.angle = 0
        self.pulse = 0

        self.setMinimumSize(420, 420)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30)

    def animate(self):
        self.angle = (self.angle + 2) % 360
        self.pulse = (self.pulse + 1) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()

        # Outer ring
        painter.setPen(QPen(QColor("#00d9ff"), 3))
        painter.drawEllipse(
            center.x() - 165,
            center.y() - 165,
            330,
            330,
        )

        # Second ring
        painter.setPen(QPen(QColor("#087eaa"), 2))
        painter.drawEllipse(
            center.x() - 135,
            center.y() - 135,
            270,
            270,
        )

        # Rotating arc
        pen = QPen(QColor("#00ffff"), 7)
        painter.setPen(pen)
        painter.drawArc(
            center.x() - 150,
            center.y() - 150,
            300,
            300,
            self.angle * 16,
            95 * 16,
        )

        # Inner rotating arc
        pen = QPen(QColor("#38bdf8"), 4)
        painter.setPen(pen)
        painter.drawArc(
            center.x() - 112,
            center.y() - 112,
            224,
            224,
            -self.angle * 12,
            70 * 16,
        )

        # Core glow
        glow = 38 + int(abs(self.pulse - 180) / 18)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#008cff"))
        painter.drawEllipse(
            center.x() - glow,
            center.y() - glow,
            glow * 2,
            glow * 2,
        )

        painter.setBrush(QColor("#d9fbff"))
        painter.drawEllipse(
            center.x() - 18,
            center.y() - 18,
            36,
            36,
        )