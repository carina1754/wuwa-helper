from __future__ import annotations

from typing import Any

from .history import list_sessions, save_session
from .models import AnalysisSession, BuildRule
from .rules import load_build_rules, save_build_rules


def export_all() -> dict[str, Any]:
    return {
        "rules": [rule.model_dump() for rule in load_build_rules()],
        "history": [session.model_dump() for session in list_sessions(limit=200)],
    }


def import_all(payload: dict[str, Any]) -> dict[str, int]:
    rules = [BuildRule.model_validate(item) for item in payload.get("rules", [])]
    sessions = [AnalysisSession.model_validate(item) for item in payload.get("history", [])]
    if rules:
        save_build_rules(rules)
    for session in sessions:
        save_session(session)
    return {"rules": len(rules), "history": len(sessions)}
