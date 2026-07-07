"""Test safety net: never run the suite against the production database.

`src/database.py` resolves `DATABASE_URL` to the production DB `wuwa_ai_coach`
when nothing else is set. This module runs at pytest collection time and, when
the resolved database is production, redirects the whole test session to the
isolated `wuwa_ai_coach_dev` database. It also stops `main.py`'s background
refresh worker from making real network calls when `test_api.py` imports the
app (explicit `refresh_pickups_and_updates(force=True)` calls in tests still
run — they use mocked fetchers).
"""
from __future__ import annotations

import os

from src.database import database_url

_root, _name = database_url().rsplit("/", 1)
if _name == "wuwa_ai_coach":
    os.environ["DATABASE_URL"] = f"{_root}/wuwa_ai_coach_dev"
os.environ.setdefault("DISABLE_CONTENT_REFRESH", "1")
