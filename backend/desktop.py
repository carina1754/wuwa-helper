"""단일 실행 프로그램 엔트리. 켜면 네이티브 창 하나로 앱 전체 사용.

- 개발: `uv run desktop.py`
- 배포: PyInstaller 로 빌드된 `띵조AI.exe` 더블클릭(파이썬/uv/브라우저 불필요)

포트는 빈 포트를 자동 선택(프로덕션 8000 충돌 회피). 로컬 LLM/DB 불필요.
AI 는 설정 탭의 NVIDIA 키(BYO)로 동작. 기록은 exe 옆 wuwa_data/ 에 파일 저장.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

HOST = "127.0.0.1"
_FROZEN = getattr(sys, "frozen", False)


def _bundle_root() -> Path:
    # PyInstaller onefile 은 리소스를 _MEIPASS 에 풀어놓음. 개발 땐 이 파일 폴더.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _persist_dir() -> Path:
    # 기록은 재실행에도 남아야 함 → frozen 이면 exe 옆, 개발이면 backend/data/local.
    if _FROZEN:
        base = Path(sys.executable).resolve().parent / "wuwa_data"
    else:
        base = Path(__file__).resolve().parent / "data" / "local"
    base.mkdir(parents=True, exist_ok=True)
    return base


# 번들 리소스/저장 경로를 env 로 고정한 뒤에 app 을 임포트해야 반영됨(모듈 로드시 경로 계산).
if _FROZEN:
    root = _bundle_root()
    os.environ.setdefault("STATIC_DIR", str(root / "static"))
    os.environ.setdefault("MEDIA_DIR", str(root / "media"))
os.environ.setdefault("LOCAL_DATA_DIR", str(_persist_dir()))

from main import app  # noqa: E402
import uvicorn  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _wait_until_up(port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) == 0:
                return
        time.sleep(0.1)


def main() -> None:
    port = int(os.environ["PORT"]) if os.environ.get("PORT") else _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))

    # 창 없이 서버만(빌드 검증용): WUWA_HEADLESS=1 이면 포그라운드로 서빙.
    if os.getenv("WUWA_HEADLESS") == "1":
        print(f"headless on http://{HOST}:{port}/", flush=True)
        server.run()
        return

    threading.Thread(target=server.run, daemon=True).start()
    _wait_until_up(port)

    import webview  # 여기서만 import (헤드리스/서버검증 땐 GUI 스택 불필요)

    webview.create_window("띵조 AI", f"http://{HOST}:{port}/", width=1280, height=860)
    webview.start()  # 창 닫으면 반환 → 프로세스 종료(daemon 서버도 같이 죽음)


if __name__ == "__main__":
    main()
