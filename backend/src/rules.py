from __future__ import annotations

import json
from pathlib import Path

from .database import get_connection
from .models import BuildRule, CharacterCatalogItem, TeamRule

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BUILD_RULES_PATH = DATA_DIR / "build_rules.json"
TEAM_RULES_PATH = DATA_DIR / "team_rules.json"


def load_build_rules(path: Path | None = None) -> list[BuildRule]:
    if path is None:
        with get_connection() as conn:
            rows = conn.execute("SELECT rule_json FROM rules ORDER BY character_name COLLATE NOCASE").fetchall()
        return [BuildRule.model_validate_json(row["rule_json"]) for row in rows]

    rule_path = path or BUILD_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [BuildRule.model_validate(item) for item in data]


def save_build_rules(rules: list[BuildRule], path: Path | None = None) -> list[BuildRule]:
    validated = [BuildRule.model_validate(rule) for rule in rules]
    if path is None:
        with get_connection() as conn:
            conn.execute("DELETE FROM rules")
            for index, rule in enumerate(validated):
                conn.execute(
                    """
                    INSERT INTO rules (id, character_name, role, rule_json, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        f"{rule.character_name.strip().lower()}:{rule.role}:{index}",
                        rule.character_name,
                        rule.role,
                        rule.model_dump_json(),
                    ),
                )
            conn.commit()
        return validated

    rule_path = path or BUILD_RULES_PATH
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    with rule_path.open("w", encoding="utf-8") as file:
        json.dump([rule.model_dump() for rule in validated], file, ensure_ascii=False, indent=2)
    return validated


def load_team_rules(path: Path | None = None) -> list[TeamRule]:
    if path is None:
        with get_connection() as conn:
            rows = conn.execute("SELECT rule_json FROM team_rules ORDER BY name COLLATE NOCASE").fetchall()
        return [TeamRule.model_validate_json(row["rule_json"]) for row in rows]

    rule_path = path or TEAM_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [TeamRule.model_validate(item) for item in data]


def load_character_catalog() -> list[CharacterCatalogItem]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT data_json
            FROM character_catalog
            ORDER BY rarity DESC, name COLLATE NOCASE
            """
        ).fetchall()
    return [CharacterCatalogItem.model_validate_json(row["data_json"]) for row in rows]


def save_character_catalog(characters: list[CharacterCatalogItem]) -> list[CharacterCatalogItem]:
    validated = [CharacterCatalogItem.model_validate(character) for character in characters]
    with get_connection() as conn:
        conn.execute("DELETE FROM character_catalog")
        for character in validated:
            conn.execute(
                """
                INSERT INTO character_catalog
                (id, name, element, weapon_type, rarity, role, data_json, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    character.id,
                    character.name,
                    character.element,
                    character.weapon_type,
                    character.rarity,
                    character.role,
                    character.model_dump_json(),
                    character.source,
                ),
            )
        conn.commit()
    return validated
