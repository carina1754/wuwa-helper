"""네이티브 앱 진입점. `python -m native` 또는 exe 부트가 호출."""
from __future__ import annotations

import os
import sys


def run() -> int:
    # 창모드 exe(console=False) 는 stdout/stderr None → isatty() 부르는 코드 보호.
    for _name in ("stdout", "stderr"):
        if getattr(sys, _name) is None:
            setattr(sys, _name, open(os.devnull, "w"))

    from PySide6.QtWidgets import QApplication

    from .app import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("띵조 AI")
    win = MainWindow()
    win.setWindowTitle("띵조 AI")
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
