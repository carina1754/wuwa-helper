# -*- coding: utf-8 -*-
"""Phase 2 catalog i18n (skills): add display-only localized siblings to
resonators.json from the datamine Textmaps:

  skills[].SkillName_{en,ja,zhHans}      (per-character active/inherent skills)
  skills[].SkillDescribe_{en,ja,zhHans}  (interpolated skill text)
  resonance_chain[].NodeName_{en,ja,zhHans}

DISPLAY ONLY. The damage engine classifies via KOREAN substring matching on
`SkillType` and `damage[].name` (frontend build.ts / partyDamage.ts), so those
fields stay Korean and are never touched here. Only additive `_en/_ja/_zhHans`
siblings are written; existing Korean values are preserved.

Parity gate: a field is localized only when the datamine KO we reproduce equals
the catalog's existing Korean value after normalization (strip `<...>` tags +
collapse whitespace). Mismatches — e.g. WIP characters whose catalog chain still
holds raw tags / uninterpolated `{i}` — are reported and skipped, never guessed.

Skill text is stored raw (mirrors how build_skills serializes SkillDescribe with
tags; Codex strips at render). Chain text is stored normalized (matches the
catalog's normalized ko convention and TeamBuilder, which does not strip tags).

Also prints the 8-value SkillType enum in en/ja/zhHans for the frontend i18n map.

Usage:
  python backend/scripts/extract_i18n_skills.py            # dry run -> report
  python backend/scripts/extract_i18n_skills.py --write    # apply to catalog
Env: DATAMINE_ROOT overrides the datamine location.
"""
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
DM = Path(os.getenv("DATAMINE_ROOT") or (ROOT / "WutheringWaves_Data"))
BIN = DM / "BinData"
CAT = ROOT / "backend" / "data" / "catalog"
LANGS = {"en": "en", "ja": "ja", "zhHans": "zh-Hans"}  # field suffix -> textmap dir
WRITE = "--write" in sys.argv


def log(s):
    print(s)


def load_list(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    if isinstance(d, dict):
        vals = list(d.values())
        if vals and all(isinstance(v, dict) for v in vals):
            return vals
        for v in vals:
            if isinstance(v, list):
                return v
    return d


def build_map(lang):
    m = {}
    for half in ("multi_text", "multi_text_1sthalf", "multi_text_2ndhalf"):
        p = DM / "Textmaps" / lang / half / "MultiText.json"
        if p.exists():
            for e in json.loads(p.read_text(encoding="utf-8")):
                if isinstance(e, dict) and "Id" in e:
                    c = e.get("Content") or ""
                    if c or str(e["Id"]) not in m:
                        m[str(e["Id"])] = c
    return m


log("datamine: %s" % DM)
MAPS = {"ko": build_map("ko")}
for _suf, _d in LANGS.items():
    MAPS[_suf] = build_map(_d)
log("map sizes: " + ", ".join("%s=%d" % (k, len(v)) for k, v in MAPS.items()))

ROLEINFO = {d["Id"]: d for d in load_list(BIN / "role/roleinfo.json")}
SKILLS_BY_GROUP = defaultdict(list)
for _s in load_list(BIN / "skill/skill.json"):
    SKILLS_BY_GROUP[_s.get("SkillGroupId")].append(_s)
SKILLTYPE = {r["Id"]: r.get("TypeName") for r in load_list(BIN / "skill/skilltype.json")}
RC = load_list(BIN / "resonate_chain/resonantchain.json")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def norm(s):
    """Storage form: drop tags, collapse whitespace to single spaces."""
    return _WS.sub(" ", _TAG.sub("", s or "")).strip()


def nows(s):
    """Parity-comparison form: drop tags AND all whitespace. The catalog joined
    former newlines with no separator ('진화한다.불멸의') while our reproduction
    keeps a space, so equality must ignore whitespace — the non-whitespace glyphs
    still have to match exactly, so genuinely different text never passes."""
    return _WS.sub("", _TAG.sub("", s or ""))


def interp(M, key, params):
    raw = M.get(str(key), "") or ""
    params = params or []

    def sub(m):
        i = int(m.group(1))
        if i < len(params) and params[i] not in (None, ""):
            return str(params[i])
        return m.group(0)

    return re.sub(r"\{(\d+)\}", sub, raw)


def desc_key(sk):
    """Choose SkillDescribe, else SkillResume — decided by the ko result, then
    the same source key is applied across languages (mirrors build_skills)."""
    if interp(MAPS["ko"], sk.get("SkillDescribe"), sk.get("SkillDetailNum")).strip():
        return sk.get("SkillDescribe"), sk.get("SkillDetailNum")
    return sk.get("SkillResume"), sk.get("SkillResumeNum")


def sibs(target, base, key, params, transform):
    """Attach {base}_{suf} siblings from datamine, applying `transform`."""
    for suf in LANGS:
        v = transform(interp(MAPS[suf], key, params))
        if v:
            target["%s_%s" % (base, suf)] = v


# --- SkillType enum (8 values) for the frontend i18n map -----------------
type_labels = {}  # ko label -> {suf: label}
for _r in load_list(BIN / "skill/skilltype.json"):
    tk = _r.get("TypeName")
    ko = norm(MAPS["ko"].get(str(tk), ""))
    if not ko:
        continue
    type_labels[ko] = {suf: norm(MAPS[suf].get(str(tk), "")) for suf in LANGS}


def localize_skills(res):
    name_ok = name_skip = desc_ok = desc_skip = chain_ok = chain_skip = 0
    for e in res:
        ri = ROLEINFO.get(e.get("id"))
        rows = sorted(
            SKILLS_BY_GROUP.get(ri.get("SkillId"), []) if ri else [],
            key=lambda x: (x.get("SortIndex") or 0, x.get("Id") or 0),
        )
        # skills — align by position, gate each field on normalized ko match
        for cs, sk in zip(e.get("skills") or [], rows):
            nkey = sk.get("SkillName") or sk.get("Name")
            if nows(interp(MAPS["ko"], nkey, None)) == nows(cs.get("SkillName")) and cs.get("SkillName"):
                sibs(cs, "SkillName", nkey, None, lambda s: s.strip())
                name_ok += 1
            else:
                name_skip += 1
            dk, dp = desc_key(sk)
            if nows(interp(MAPS["ko"], dk, dp)) == nows(cs.get("SkillDescribe")) and cs.get("SkillDescribe"):
                sibs(cs, "SkillDescribe", dk, dp, lambda s: s.strip())
                desc_ok += 1
            else:
                desc_skip += 1
        # resonance chain — align by GroupIndex, store normalized
        nodes = sorted(
            [r for r in RC if ri and r.get("GroupId") == ri.get("SkillId")],
            key=lambda r: (r.get("GroupIndex") or 0, r.get("Id") or 0),
        )
        for cn, node in zip(e.get("resonance_chain") or [], nodes):
            akey = node.get("AttributesDescription")
            aparams = node.get("AttributesDescriptionParams")
            if nows(interp(MAPS["ko"], akey, aparams)) == nows(cn.get("NodeName")) and cn.get("NodeName"):
                sibs(cn, "NodeName", akey, aparams, norm)
                chain_ok += 1
            else:
                chain_skip += 1
    log("skills: name ok=%d skip=%d | desc ok=%d skip=%d | chain ok=%d skip=%d"
        % (name_ok, name_skip, desc_ok, desc_skip, chain_ok, chain_skip))


res = json.loads((CAT / "resonators.json").read_text(encoding="utf-8"))
localize_skills(res)

log("\n--- SkillType enum (%d values) ---" % len(type_labels))
for ko, tr in sorted(type_labels.items()):
    log("  %s => en=%r ja=%r zhHans=%r" % (ko, tr["en"], tr["ja"], tr["zhHans"]))

if WRITE:
    (CAT / "resonators.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log("\nWROTE resonators.json")
else:
    log("\nDRY RUN (pass --write to apply).")
