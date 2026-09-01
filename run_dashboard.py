import sys

from PySide6.QtWidgets import QApplication

from interface.runtime_dashboard import JarvisRuntimeHUD


def main() -> None:
    app = QApplication(sys.argv)
    window = JarvisRuntimeHUD()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
