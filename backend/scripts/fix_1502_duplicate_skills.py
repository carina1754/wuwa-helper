"""Collapse duplicate resonator skill rows in the authoritative catalog file.

Datamine ingest emitted two tiers for a few of 방랑자·회절(1502)'s skills — a
damage-bearing base row and a longer "enhanced" description row with an empty
``damage`` array — surfacing the same skill twice in the codex. This merges each
duplicate ``(SkillType, SkillName)`` group into one entry: the damage-bearing
row is kept in place, but adopts the richest (longest) description available.

The rewrite is a **format-preserving surgical splice**: only the affected
character's JSON object is re-serialized (indent=2, matching the file style) and
spliced back into the raw text, so every other byte is left untouched and the
diff stays minimal on this authoritative file. Idempotent — a second run is a
no-op. Deploy = backend restart (catalog is @lru_cache file-primary).

Usage: uv run python scripts/fix_1502_duplicate_skills.py
"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "data" / "catalog" / "resonators.json"


def _merge_skills(skills: list[dict]) -> list[dict]:
    """One entry per (SkillType, SkillName); keep damage-richest row, desc-richest text."""
    order: list[tuple] = []
    groups: dict[tuple, list[dict]] = {}
    for s in skills:
        key = (s.get("SkillType"), s.get("SkillName"))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(s)

    out: list[dict] = []
    for key in order:
        rows = groups[key]
        if len(rows) == 1:
            out.append(rows[0])
            continue
        base = max(rows, key=lambda r: len(r.get("damage") or []))  # preserve engine dmg
        richest = max(rows, key=lambda r: len(r.get("SkillDescribe") or ""))  # fullest text
        merged = dict(base)
        merged["SkillDescribe"] = richest.get("SkillDescribe")
        out.append(merged)
    return out


def _object_span(raw: str, needle: str) -> tuple[int, int]:
    """Byte span [start, end) of the top-level object containing ``needle``.

    Scans forward from the object's opening brace, brace-counting while honoring
    string literals and escapes, and returns the position just past its match.
    """
    pos = raw.index(needle)
    start = raw.rindex("{", 0, pos)
    depth = 0
    in_str = False
    esc = False
    i = start
    while i < len(raw):
        c = raw[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1
        i += 1
    raise ValueError("unbalanced object")


def _serialize_at_indent(obj: dict, base_indent: int) -> str:
    """json.dumps(indent=2) re-indented so the object sits at ``base_indent`` spaces."""
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    pad = " " * base_indent
    lines = text.split("\n")
    return lines[0] + "\n" + "\n".join(pad + ln for ln in lines[1:])


def main() -> None:
    raw = CATALOG.read_text(encoding="utf-8")
    res = json.loads(raw)

    targets = []
    for r in res:
        skills = r.get("skills") or []
        merged = _merge_skills(skills)
        if len(merged) != len(skills):
            targets.append((r, merged, len(skills)))

    if not targets:
        print("no duplicate skills found - nothing to do")
        return

    # splice from the end so earlier spans keep their offsets
    edits = []
    for r, merged, old_n in targets:
        start, end = _object_span(raw, f'"id": {r.get("id")},')
        # detect the object's base indent (leading spaces before its '{')
        line_start = raw.rindex("\n", 0, start) + 1
        base_indent = start - line_start
        new_obj = dict(r)
        new_obj["skills"] = merged
        edits.append((start, end, _serialize_at_indent(new_obj, base_indent)))
        print(f"  id {r.get('id')} {r.get('name')}: {old_n} -> {len(merged)} skills")

    for start, end, text in sorted(edits, reverse=True):
        raw = raw[:start] + text + raw[end:]

    # parse-back guard: data must be intact
    json.loads(raw)
    CATALOG.write_text(raw, encoding="utf-8")
    print(f"rewrote {CATALOG.name}; {len(targets)} character(s) deduped (surgical splice)")


if __name__ == "__main__":
    main()
