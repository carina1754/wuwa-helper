"""네이티브 데스크톱 창으로 실행(브라우저 X). FastAPI+정적 프론트를 한 창에 띄운다.

    uv run desktop.py

포트는 자동으로 빈 포트를 잡으므로 프로덕션(8000)과 충돌하지 않는다.
로컬 LLM/DB 불필요, AI 는 설정 탭의 NVIDIA 키(BYO)로 동작.
"""
from __future__ import annotations

import socket
import threading
import time

import uvicorn
import webview

from main import app

HOST = "127.0.0.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_until_up(port: int, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) == 0:
                return
        time.sleep(0.1)


if __name__ == "__main__":
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    _wait_until_up(port)

    webview.create_window("띵조 AI", f"http://{HOST}:{port}/", width=1280, height=860)
    webview.start()  # 창 닫으면 프로세스 종료(daemon 스레드도 같이 죽음)
