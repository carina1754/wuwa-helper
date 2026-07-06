from __future__ import annotations

from .database import get_connection
from .models import BuildRule, CharacterCatalogItem, TeamRule


def load_build_rules() -> list[BuildRule]:
    with get_connection() as conn:
        rows = conn.execute("SELECT rule_json FROM rules ORDER BY character_name COLLATE \"C\"").fetchall()
    return [BuildRule.model_validate_json(row["rule_json"]) for row in rows]


def save_build_rules(rules: list[BuildRule]) -> list[BuildRule]:
    validated = [BuildRule.model_validate(rule) for rule in rules]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM rules")
            for index, rule in enumerate(validated):
                cur.execute(
                    """
                    INSERT INTO rules (id, character_name, role, rule_json, updated_at)
                    VALUES (%s, %s, %s, %s, now())
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


def load_team_rules() -> list[TeamRule]:
    with get_connection() as conn:
        rows = conn.execute("SELECT rule_json FROM team_rules ORDER BY name COLLATE \"C\"").fetchall()
    return [TeamRule.model_validate_json(row["rule_json"]) for row in rows]


def save_team_rules(rules: list[TeamRule]) -> list[TeamRule]:
    validated = [TeamRule.model_validate(rule) for rule in rules]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM team_rules")
            for index, rule in enumerate(validated):
                cur.execute(
                    """
                    INSERT INTO team_rules (id, name, core_character, rule_json, updated_at)
                    VALUES (%s, %s, %s, %s, now())
                    """,
                    (f"{rule.name.strip().lower()}:{index}", rule.name, rule.core_character, rule.model_dump_json()),
                )
        conn.commit()
    return validated


def load_character_catalog() -> list[CharacterCatalogItem]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT data_json
            FROM character_catalog
            ORDER BY rarity DESC NULLS LAST, name COLLATE "C"
            """
        ).fetchall()
    return [CharacterCatalogItem.model_validate_json(row["data_json"]) for row in rows]


def save_character_catalog(characters: list[CharacterCatalogItem]) -> list[CharacterCatalogItem]:
    validated = [CharacterCatalogItem.model_validate(character) for character in characters]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM character_catalog")
            for character in validated:
                cur.execute(
                    """
                    INSERT INTO character_catalog
                    (id, name, element, weapon_type, rarity, role, data_json, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
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