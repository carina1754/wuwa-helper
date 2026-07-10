"""Refresh catalog skill rates from the (updatable) local datamine clone.

The runtime catalog (data/catalog/resonators.json) is file-primary. New/updated
characters can ship with placeholder or beta skill damage while unreleased; once
the datamine clone is re-pulled for a later ResVer, this re-extracts the correct
per-level rates and patches only the characters whose damage actually changed.

Only skills[] is rewritten (display data; not used by the damage engine). A
character is touched when its damage rates differ, when its stored description
still has raw {i} placeholders that a fresh extract fills (older adds skipped the
SkillDetailNum interpolation), or when its id needs the legacy str->int fix.
General description-only wording drift is otherwise left alone to keep diffs
focused on real corrections.

Datamine root: DATAMINE_ROOT env, else the updatable clone <repo>/WutheringWaves_Data.
Idempotent. Dry-run by default; pass --apply to write.

    uv run python scripts/refresh_skills_from_datamine.py            # preview
    uv run python scripts/refresh_skills_from_datamine.py --apply    # write
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
# Default to the user-maintained updatable clone (no -3.5 suffix); overridable.
os.environ.setdefault("DATAMINE_ROOT", str(REPO / "WutheringWaves_Data"))
sys.path.insert(0, str(BACKEND / "scripts"))

import extract_from_datamine as dm  # noqa: E402  (binds DATAMINE_ROOT at import)

CAT = BACKEND / "data" / "catalog" / "resonators.json"


def _dmg_sig(skills: list) -> list:
    """Damage-only signature: name + per-level rates, ignoring description text."""
    return [
        (s.get("SkillType"), s.get("SkillName"),
         [(d.get("name"), d.get("rates")) for d in (s.get("damage") or [])])
        for s in (skills or [])
    ]


def _blocks(skills: list) -> int:
    return sum(len(s.get("damage") or []) for s in (skills or []))


def _desc_bad(skills: list) -> int:
    """Count skills whose SkillDescribe is blank or still carries an un-interpolated
    {i} placeholder — descriptions a fresh extract could fill (interpolation or the
    SkillResume fallback). A drop in this count means the extract is an improvement."""
    n = 0
    for s in (skills or []):
        d = s.get("SkillDescribe") or ""
        if not d.strip() or re.search(r"\{\d+\}", d):
            n += 1
    return n


def main(apply: bool) -> int:
    data = json.loads(CAT.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else list(data.values())
    changed = []
    for r in rows:
        rid = r.get("id")
        try:
            iid = int(rid)
        except (TypeError, ValueError):
            print(f"  WARN {rid!r}: non-numeric id, skipped")
            continue
        new = dm.build_skills(iid)
        if not isinstance(new, list) or _blocks(new) <= 0:
            # Degenerate extraction (unreleased/missing in this clone) — never
            # overwrite existing good data with nothing.
            continue
        old = r.get("skills") or []
        dmg_changed = _dmg_sig(new) != _dmg_sig(old)
        id_fix = not isinstance(rid, int)
        desc_fix = _desc_bad(new) < _desc_bad(old)
        if not (dmg_changed or id_fix or desc_fix):
            continue
        changed.append((rid, r.get("name"), _blocks(old), _blocks(new), dmg_changed, id_fix, desc_fix))
        if apply:
            r["skills"] = new
            if id_fix:
                r["id"] = iid

    print(f"datamine_root = {dm.DM}")
    print(f"characters needing update: {len(changed)}")
    for rid, name, ob, nb, dch, idf, dscf in changed:
        flags = []
        if dch:
            flags.append(f"dmgblocks {ob}->{nb}")
        if dscf:
            flags.append("desc gaps filled")
        if idf:
            flags.append("id str->int")
        print(f"  {rid} {name}: {', '.join(flags)}")

    if not changed:
        print("nothing to do (catalog already matches this datamine clone).")
        return 0
    if apply:
        CAT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"WROTE {CAT}  (restart backend to deploy)")
    else:
        print("(dry-run; re-run with --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--apply" in sys.argv))
