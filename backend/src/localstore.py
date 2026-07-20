"""로컬 JSON 파일 저장소 (Postgres 대체, 스탠드얼론 단일 로컬 유저).

기본 경로: backend/data/local/ (env LOCAL_DATA_DIR 로 override).
frozen exe(PyInstaller)는 _MEIPASS 임시폴더라 종료 시 증발 → %LOCALAPPDATA%\\띵조AI 에 영속 저장.
쓰기는 temp+os.replace 로 원자적(부분쓰기·손상 방지).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    override = os.getenv("LOCAL_DATA_DIR")
    if override:
        base = Path(override)
    elif getattr(sys, "frozen", False):
        base = Path(os.getenv("LOCALAPPDATA") or Path.home()) / "띵조AI"
    else:
        base = Path(__file__).resolve().parents[1] / "data" / "local"
    base.mkdir(parents=True, exist_ok=True)
    return base


def read_json(name: str, default: Any) -> Any:
    path = data_dir() / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(name: str, obj: Any) -> None:
    path = data_dir() / name
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
