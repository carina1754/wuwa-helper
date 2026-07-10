"""Resonance chain (공명 사슬) effect layer — sequence Sn → param-grounded deltas.

Loads ``data/catalog/resonance_effects.json`` (per-character, node-indexed effects,
each number grounded in a datamine ``AttributesDescriptionParams`` value — never
fabricated) and resolves the owned nodes S1..``sequence`` into engine-consumable
deltas: self/team stat buffs, a general damage%, DEF-ignore / RES-shred, per-skill
multiplier & damage boosts, and extra damage instances (summons / 추가타).

Effects flagged ``cond`` are trigger/stack/duration-gated; they apply only under the
full-uptime assumption (mirrors the weapon conditional-buff / "풀 업타임" convention).
Anything ungroundable or purely mechanical/utility is carried as a ``note`` (surfaced
to the UI, never folded into damage). Memoized -> data changes need a process restart.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .stats import STAT_KEYS, Buff

_EFFECTS_PATH = Path(__file__).resolve().parents[2] / "data" / "catalog" / "resonance_effects.json"
_MAX_DEF_IGNORE = 0.95


@lru_cache(maxsize=1)
def _load_effects() -> dict:
    try:
        return json.loads(_EFFECTS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


@dataclass
class ChainResolved:
    """Owned-sequence effects, split into how the engine consumes each."""

    self_stats: list[Buff] = field(default_factory=list)  # (key, value) for compute_stats extra
    team_stats: list[Buff] = field(default_factory=list)  # (key, value) granted to the whole party
    dmg_pct: float = 0.0  # → opts.bonus_pct (general damage%)
    def_ignore: float = 0.0  # fraction 0..1, added to opts.def_ignore
    res_shred: float = 0.0  # fraction 0..1, added to opts.res_shred
    per_skill: list[dict] = field(default_factory=list)  # {skill_name, kind:'mult'|'dmg', amount}
    extra_hits: list[dict] = field(default_factory=list)  # {name, skill_type, element, mult, hits, always_crit}
    notes: list[dict] = field(default_factory=list)  # {text, reason, node}

    def is_empty(self) -> bool:
        return not (
            self.self_stats
            or self.team_stats
            or self.dmg_pct
            or self.def_ignore
            or self.res_shred
            or self.per_skill
            or self.extra_hits
        )


def _num(effect: dict, *keys: str) -> float | None:
    """First numeric value among ``keys`` (grounding numbers arrive as int/float)."""
    for k in keys:
        v = effect.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def resolve_chain(
    reso_id: str | int,
    sequence: int,
    full_uptime: bool = False,
    char_element: str | None = None,
    effects: dict | None = None,
) -> ChainResolved:
    """Resolve owned nodes S1..``sequence`` for one character into engine deltas.

    ``effects`` overrides the cached data file (for testing). Conditional effects are
    dropped unless ``full_uptime``; unrecognized / ungroundable ones are ignored here
    (they should already be ``note`` kinds in the data).
    """
    out = ChainResolved()
    if not sequence or sequence < 1:
        return out
    data = effects if effects is not None else _load_effects()
    entry = data.get(str(reso_id))
    if not entry:
        return out
    nodes = entry.get("nodes") if isinstance(entry, dict) else entry
    if not isinstance(nodes, dict):
        return out

    for idx in range(1, min(int(sequence), 6) + 1):
        for e in nodes.get(str(idx)) or []:
            kind = e.get("kind")
            if kind == "note":
                out.notes.append({"text": e.get("text"), "reason": e.get("reason"), "node": idx})
                continue
            if e.get("cond") and not full_uptime:
                continue
            if kind == "stat":
                key, val = e.get("key"), _num(e, "value")
                if key in STAT_KEYS and val is not None:
                    out.self_stats.append((key, val))
            elif kind == "team_stat":
                key, val = e.get("key"), _num(e, "value")
                if key in STAT_KEYS and val is not None:
                    out.team_stats.append((key, val))
            elif kind == "dmg_pct":
                out.dmg_pct += _num(e, "value") or 0.0
            elif kind == "def_ignore":
                out.def_ignore += (_num(e, "value") or 0.0) / 100.0
            elif kind == "res_shred":
                out.res_shred += (_num(e, "value") or 0.0) / 100.0
            elif kind == "skill_mult":
                nm, val = e.get("skill_name"), _num(e, "add_pct", "value")
                if nm and val is not None:
                    out.per_skill.append({"skill_name": nm, "kind": "mult", "amount": val})
            elif kind == "skill_dmg":
                nm, val = e.get("skill_name"), _num(e, "value")
                if nm and val is not None:
                    out.per_skill.append({"skill_name": nm, "kind": "dmg", "amount": val})
            elif kind == "extra_hit":
                mult = _num(e, "mult")
                if mult is not None:
                    out.extra_hits.append(
                        {
                            "name": e.get("name") or "공명 사슬 추가타",
                            "skill_type": e.get("skill_type") or "없음",
                            "element": e.get("element") or char_element,
                            "mult": mult,
                            "hits": _num(e, "hits") or 1.0,
                            "always_crit": bool(e.get("always_crit")),
                        }
                    )
    out.def_ignore = min(_MAX_DEF_IGNORE, out.def_ignore)
    return out
