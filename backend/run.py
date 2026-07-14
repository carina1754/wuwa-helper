"""스탠드얼론 실행기: 한 프로세스로 API + 정적 프론트엔드 서빙 후 브라우저 오픈.

DB/로컬 LLM 불필요. AI 기능은 설정 탭에서 넣은 NVIDIA API 키(BYO)로 동작.
기록/로그는 backend/data/local/ 에 파일로 저장(로그인 없음).

    uv run run.py           # 기본 127.0.0.1:8000
    PORT=9000 uv run run.py # 포트 변경
"""
from __future__ import annotations

import os
import threading
import webbrowser

import uvicorn

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "9000"))  # 8000 은 라이브 프로덕션이 점유


def _open_browser() -> None:
    # 서버 뜰 시간 주고 연다(로컬이라 1.5s 충분).
    threading.Timer(1.5, lambda: webbrowser.open(f"http://{HOST}:{PORT}/")).start()


if __name__ == "__main__":
    if os.getenv("NO_BROWSER") != "1":
        _open_browser()
    uvicorn.run("main:app", host=HOST, port=PORT, log_level="info")
