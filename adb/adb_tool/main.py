"""Application entry point."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from adb_tool.main_window import MainWindow
from adb_tool.utils.logger import setup_logger


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)


def main():
    setup_logger()
    
    app = QApplication(sys.argv)
    app.setApplicationName("ADB 日志查看器")
    app.setApplicationVersion("2.0.0")
    app.setWindowIcon(QIcon(resource_path("tubiao.ico")))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
