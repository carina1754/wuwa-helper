from __future__ import annotations

from typing import Any

from .models import BuildRule, CharacterSnapshot, Diagnosis, EchoItem, Grade, Role


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def grade_for_score(score: int) -> Grade:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "keep"
    if score >= 50:
        return "upgrade"
    if score >= 30:
        return "hold"
    if score >= 10:
        return "replace"
    return "discard"


def choose_rule(character_name: str | None, rules: list[BuildRule], fallback_role: Role) -> BuildRule:
    wanted_name = _norm(character_name)
    for rule in rules:
        if wanted_name and _norm(rule.character_name) == wanted_name:
            return rule
    fallback_name = f"default_{fallback_role}"
    for rule in rules:
        if _norm(rule.character_name) == fallback_name:
            return rule
    for rule in rules:
        if rule.role == fallback_role:
            return rule
    return rules[0]


def evaluate_echo(echo: EchoItem, rule: BuildRule) -> Diagnosis:
    score = 0
    reasons: list[str] = []
    actions: list[str] = []
    recommended_sets = {_norm(item) for item in rule.recommended_sets}
    priority_stats = {_norm(item) for item in rule.priority_stats}
    useful_sub_stats = {_norm(item) for item in rule.useful_sub_stats}
    bad_sub_stats = {_norm(item) for item in rule.bad_sub_stats}

    if _norm(echo.set_name) in recommended_sets:
        score += 20
        reasons.append("Echo set matches a recommended set.")
    else:
        actions.append("Replace this echo with one from a recommended set.")

    if _norm(echo.main_stat) in priority_stats:
        score += 25
        reasons.append("Main stat matches the build priority.")
    else:
        actions.append("Farm an echo with a priority main stat.")

    sub_stat_names = {_norm(stat.name) for stat in echo.sub_stats if stat.name}
    useful_hits = len(sub_stat_names & useful_sub_stats)
    bad_hits = len(sub_stat_names & bad_sub_stats)
    score += useful_hits * 15
    score -= bad_hits * 15
    if useful_hits:
        reasons.append(f"{useful_hits} useful sub-stat(s) found.")
    if bad_hits:
        reasons.append(f"{bad_hits} low-value sub-stat(s) found.")
        actions.append("Avoid investing more unless this slot is temporary.")
    if {"crit rate", "crit dmg"}.issubset(sub_stat_names):
        score += 10
        reasons.append("Crit Rate and Crit DMG are both present.")

    score = max(0, min(100, score))
    if echo.level is not None and echo.level < 25 and score >= 60:
        actions.append("This echo is worth leveling further.")
    if not actions:
        actions.append("Keep this echo unless a stronger replacement appears.")

    return Diagnosis(
        target_type="echo",
        target_name=echo.name or echo.slot,
        grade=grade_for_score(score),
        score=score,
        reasons=reasons or ["Not enough echo data to score confidently."],
        recommended_actions=actions,
    )


def evaluate_character(snapshot: CharacterSnapshot, rule: BuildRule) -> list[Diagnosis]:
    echo_diagnoses = [evaluate_echo(echo, rule) for echo in snapshot.echoes]
    echo_scores = [diagnosis.score for diagnosis in echo_diagnoses]
    average = round(sum(echo_scores) / len(echo_scores)) if echo_scores else 0
    reasons = [f"Average echo score is {average}."]
    actions = ["Fix the lowest-scoring echo first.", "Prioritize main stats before chasing perfect sub-stats."]
    if snapshot.weapon and snapshot.weapon.name in rule.recommended_weapons:
        average = min(100, average + 10)
        reasons.append("Weapon is listed as recommended.")
    elif rule.recommended_weapons:
        actions.append("Compare the current weapon against recommended options.")
    character_diagnosis = Diagnosis(
        target_type="character",
        target_name=snapshot.character_name,
        grade=grade_for_score(average),
        score=average,
        reasons=reasons,
        recommended_actions=actions,
    )
    return echo_diagnoses + [character_diagnosis]


def evaluate_account(profile: dict[str, Any]) -> list[Diagnosis]:
    owned = profile.get("characters", [])
    score = 50 if owned else 20
    return [
        Diagnosis(
            target_type="account",
            target_name="Account plan",
            grade=grade_for_score(score),
            score=score,
            reasons=["MVP account evaluation uses submitted character list only."],
            recommended_actions=[
                "Build one main DPS first.",
                "Add one support and one sub DPS before optimizing luxury upgrades.",
            ],
        )
    ]
