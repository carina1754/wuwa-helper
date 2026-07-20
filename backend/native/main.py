"""네이티브 앱 진입점. `python -m native` 또는 exe 부트가 호출."""
from __future__ import annotations

import os
import sys


def run() -> int:
    # 창모드 exe(console=False) 는 stdout/stderr None → isatty() 부르는 코드 보호.
    for _name in ("stdout", "stderr"):
        if getattr(sys, _name) is None:
            setattr(sys, _name, open(os.devnull, "w"))

    from pathlib import Path

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .app import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("띵조 AI")
    # 로고 — frozen 이면 _MEIPASS/media, 개발이면 backend/media
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    logo = base / "media" / "logo.png"
    if logo.exists():
        app.setWindowIcon(QIcon(str(logo)))
    win = MainWindow()
    win.setWindowTitle("띵조 AI")
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
