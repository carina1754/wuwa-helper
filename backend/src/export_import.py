from __future__ import annotations

from typing import Any

from .history import list_sessions, save_session
from .models import AnalysisSession, BuildRule, CharacterCatalogItem
from .rules import load_build_rules, load_character_catalog, save_build_rules, save_character_catalog


def export_all() -> dict[str, Any]:
    return {
        "rules": [rule.model_dump() for rule in load_build_rules()],
        "characters": [character.model_dump() for character in load_character_catalog()],
        "history": [session.model_dump() for session in list_sessions(limit=200)],
    }


def import_all(payload: dict[str, Any]) -> dict[str, int]:
    rules = [BuildRule.model_validate(item) for item in payload.get("rules", [])]
    characters = [CharacterCatalogItem.model_validate(item) for item in payload.get("characters", [])]
    sessions = [AnalysisSession.model_validate(item) for item in payload.get("history", [])]
    if rules:
        save_build_rules(rules)
    if characters:
        save_character_catalog(characters)
    for session in sessions:
        save_session(session)
    return {"rules": len(rules), "characters": len(characters), "history": len(sessions)}
