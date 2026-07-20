"""로컬 설정(파일 저장). BYO NVIDIA 키·모델·언어.

localStorage 대체: 브라우저가 없으니 localstore JSON 파일에 저장.
키는 서버 로그/기록에 절대 안 남기고 이 파일에만 둔다(사용자 소유 로컬 머신).
"""
from __future__ import annotations

from src import localstore

_FILE = "settings.json"
_DEFAULT = {"nvidia_key": "", "model": "", "language": "ko", "theme": "dark"}

LANGUAGES = ("ko", "en", "ja", "zhHans")


def load() -> dict:
    data = localstore.read_json(_FILE, {})
    return {**_DEFAULT, **(data if isinstance(data, dict) else {})}


def save(**changes) -> dict:
    data = load()
    data.update({k: v for k, v in changes.items() if k in _DEFAULT})
    localstore.write_json(_FILE, data)
    return data


if __name__ == "__main__":  # smoke: round-trip a key without clobbering real settings
    import os
    import tempfile

    os.environ["LOCAL_DATA_DIR"] = tempfile.mkdtemp()
    assert load()["language"] == "ko"
    save(nvidia_key="nvapi-x", model="m", language="ja")
    got = load()
    assert got == {"nvidia_key": "nvapi-x", "model": "m", "language": "ja"}, got
    print("settings ok")
