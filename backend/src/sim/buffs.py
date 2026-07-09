"""Buff-semantics layer (sim_buff / A2) — free-text → stat deltas.

Faithful port of build.ts's ``parseSetEffect`` / ``activeSetBonuses`` /
``weaponDescAtRank`` / ``weaponBuffs``. These read Korean sonata-set and weapon
passive descriptions and turn the recognized "…가 N% 증가" phrases into
``(StatKey, value)`` deltas the numeric engine (``stats.compute_stats``) consumes
via its ``extra`` argument. Parsing is conservative: only recognized stat phrases
are captured; anything ambiguous is left out (matching the client oracle exactly).

This is the seam A2 extends with character-kit / resonance / team buffs (via the
local-LLM parser); the set/weapon parsers below are the proven baseline.
"""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Mapping

from .stats import Buff, ResonatorBuild

# element (한글) → damage-bonus stat key
ELEM_DMG: dict[str, str] = {
    "응결": "glacioDmg",
    "용융": "fusionDmg",
    "전도": "electroDmg",
    "기류": "aeroDmg",
    "회절": "spectroDmg",
    "인멸": "havocDmg",
}


def parse_set_effect(text: str | None) -> Buff | None:
    """Parse one always-on set effect ("용융 피해가 10% 증가된다") → (key, value)."""
    if not text:
        return None
    m = re.search(r"([가-힣·\s]+?)(?:가|이)\s*([\d.]+)%\s*증가", text)
    if not m:
        return None
    value = float(m.group(2))
    name = m.group(1).strip()
    for el, k in ELEM_DMG.items():
        if el in name:
            return (k, value)
    if "공명 스킬" in name:
        return ("skillDmg", value)
    if "공명 해방" in name:
        return ("liberationDmg", value)
    if "일반 공격" in name:
        return ("basicDmg", value)
    if "강공격" in name:
        return ("heavyDmg", value)
    if "공격력" in name:
        return ("atkPct", value)
    if "방어력" in name:
        return ("defPct", value)
    if "HP" in name:
        return ("hpPct", value)
    if "크리티컬 피해" in name:
        return ("critDmg", value)
    if "크리티컬" in name:
        return ("crit", value)
    if "공명 효율" in name:
        return ("energyRegen", value)
    if "치료" in name:
        return ("healing", value)
    return None


def sonata_bonuses_from_counts(
    counts: Mapping[str, int],
    set_by_name: Mapping[str, Mapping[str, Any]],
) -> dict | None:
    """Given per-set equipped counts, return the dominant set's 2-/5-piece effects."""
    best: tuple[str, int] | None = None
    for name, count in counts.items():
        if count >= 2 and (best is None or count > best[1]):
            best = (name, count)
    if not best:
        return None
    st = set_by_name.get(best[0])
    bonuses: list[Buff] = []
    two = parse_set_effect(st.get("two_piece") if st else None)
    if two:
        bonuses.append(two)
    if best[1] >= 5:
        five = parse_set_effect(st.get("five_piece") if st else None)
        if five:
            bonuses.append(five)
    return {"name": best[0], "count": best[1], "bonuses": bonuses}


def active_set_bonuses(
    build: ResonatorBuild,
    echo_sonata: Callable[[str], list[str]],
    set_by_name: Mapping[str, Mapping[str, Any]],
) -> dict | None:
    """The set with the most equipped echoes; its 2-set (and 5-set at 5) effects apply."""
    counts: dict[str, int] = {}
    for e in build.echoes:
        if not e:
            continue
        for s in echo_sonata(e.echo_id):
            counts[s] = counts.get(s, 0) + 1
    return sonata_bonuses_from_counts(counts, set_by_name)


# --- weapon passives ---------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_SLASH_RE = re.compile(r"(\d+(?:\.\d+)?%?)(?:\s*/\s*\d+(?:\.\d+)?%?)+")


def weapon_desc_at_rank(desc: str | None, rank: int) -> str:
    """Substitute each slash-list ("4%/6.2%/…/12.8%") with the value for ``rank`` (1-5)."""
    text = _TAG_RE.sub("", desc or "")

    def repl(m: re.Match) -> str:
        parts = [p.strip() for p in m.group(0).split("/")]
        idx = min(max(rank - 1, 0), len(parts) - 1)
        return parts[idx]

    return _SLASH_RE.sub(repl, text)


WEAPON_ELEM_DMG: list[tuple[str, str]] = [
    ("응결", "glacioDmg"),
    ("용융", "fusionDmg"),
    ("전도", "electroDmg"),
    ("기류", "aeroDmg"),
    ("회절", "spectroDmg"),
    ("인멸", "havocDmg"),
]
# a sentence is conditional if it names a trigger/gate rather than a flat buff
WEAPON_COND_RE = re.compile(
    r"시|경우|후|때|이상|이하|발동|추가|입힌|입힐|명중|처치|소모|획득|전환|스택|중첩|상태|동안"
)
_SINGLES: list[tuple[str, str]] = [
    (r"일반\s*공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", "basicDmg"),
    (r"강공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", "heavyDmg"),
    (r"공명\s*스킬\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", "skillDmg"),
    (r"공명\s*해방\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", "liberationDmg"),
    (r"공격력[이가]\s*([\d.]+)\s*%\s*증가", "atkPct"),
    (r"방어력[이가]\s*([\d.]+)\s*%\s*증가", "defPct"),
    (r"(?:HP|생명력)[이가]\s*([\d.]+)\s*%\s*증가", "hpPct"),
    (r"크리티컬\s*피해[를이가을]?\s*([\d.]+)\s*%\s*증가", "critDmg"),
    (r"크리티컬[이가]\s*([\d.]+)\s*%\s*증가", "crit"),
    (r"공명\s*효율[이가]?\s*([\d.]+)\s*%\s*증가", "energyRegen"),
]


def _weapon_desc(weapon: Any) -> str | None:
    if not weapon:
        return None
    return weapon.get("desc") if isinstance(weapon, Mapping) else getattr(weapon, "desc", None)


def weapon_buffs(weapon: Any, rank: int) -> dict:
    """Split a weapon passive into ALWAYS-on vs CONDITIONAL stat deltas + a boost %.

    Each clause is scaled to ``rank`` and multiplied by its "최대 N 스택" count.
    Trigger-gated sentences (see ``WEAPON_COND_RE``) go to ``conditional``/``boost``.
    """
    always: dict[str, float] = {}
    cond: dict[str, float] = {}
    boost = 0.0
    desc = _weapon_desc(weapon)
    if not desc:
        return {"always": [], "conditional": [], "boost": 0.0}
    text = weapon_desc_at_rank(desc, rank)
    # split on sentence boundaries, but NOT on the "." inside decimals (25.6%)
    for sentence in re.split(r"[。\n]+|\.(?!\d)", text):
        if not sentence.strip():
            continue
        conditional = bool(WEAPON_COND_RE.search(sentence))
        bucket = cond if conditional else always
        sm = re.search(r"최대\s*(\d+)\s*스택", sentence)
        stacks = max(1, int(sm.group(1))) if sm else 1

        def add(key: str, v: float, bucket: dict = bucket, stacks: int = stacks) -> None:
            bucket[key] = bucket.get(key, 0) + v * stacks

        # "전체 속성 피해 보너스가 N% 증가" → all six element keys
        for m in re.finditer(r"전체\s*속성\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", sentence):
            for _, key in WEAPON_ELEM_DMG:
                add(key, float(m.group(1)))
        # "일반 공격, 강공격 피해 보너스가 N% 증가" → both; consume so singles don't double-count

        def _both(m: re.Match) -> str:
            add("basicDmg", float(m.group(1)))
            add("heavyDmg", float(m.group(1)))
            return " "

        rest = re.sub(
            r"일반\s*공격,\s*강공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", _both, sentence
        )
        for pat, key in _SINGLES:
            for m in re.finditer(pat, rest):
                add(key, float(m.group(1)))
        for name, key in WEAPON_ELEM_DMG:
            for m in re.finditer(
                name + r"\s*(?:효과\s*)?피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가", rest
            ):
                add(key, float(m.group(1)))
        # boost clauses ("… N% 부스트") — trigger-gated
        for m in re.finditer(r"([\d.]+)\s*%\s*부스트", rest):
            boost += float(m.group(1)) * stacks

    def to_arr(o: dict[str, float]) -> list[Buff]:
        return [(k, v) for k, v in o.items() if math.isfinite(v) and v != 0]

    return {"always": to_arr(always), "conditional": to_arr(cond), "boost": boost}
