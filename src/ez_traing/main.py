import argparse
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from ez_traing.ui.main_window import AppWindow


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Fluent 风格标注工具")
    parser.add_argument("--smoke-test", action="store_true", help="启动后短时间内退出")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or [])

    app = QApplication(sys.argv)
    app.setApplicationName("FluentLabel")
    setTheme(Theme.LIGHT)

    window = AppWindow()
    window.show()

    if args.smoke_test:
        QTimer.singleShot(800, app.quit)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
