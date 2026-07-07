from __future__ import annotations

from .database import get_connection
from .models import BuildRule, TeamRule


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