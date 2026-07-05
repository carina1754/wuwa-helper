from __future__ import annotations

import json
from pathlib import Path

from .models import BuildRule, TeamRule

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BUILD_RULES_PATH = DATA_DIR / "build_rules.json"
TEAM_RULES_PATH = DATA_DIR / "team_rules.json"


def load_build_rules(path: Path | None = None) -> list[BuildRule]:
    rule_path = path or BUILD_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [BuildRule.model_validate(item) for item in data]


def save_build_rules(rules: list[BuildRule], path: Path | None = None) -> list[BuildRule]:
    rule_path = path or BUILD_RULES_PATH
    rule_path.parent.mkdir(parents=True, exist_ok=True)
    validated = [BuildRule.model_validate(rule) for rule in rules]
    with rule_path.open("w", encoding="utf-8") as file:
        json.dump([rule.model_dump() for rule in validated], file, ensure_ascii=False, indent=2)
    return validated


def load_team_rules(path: Path | None = None) -> list[TeamRule]:
    rule_path = path or TEAM_RULES_PATH
    with rule_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return [TeamRule.model_validate(item) for item in data]
