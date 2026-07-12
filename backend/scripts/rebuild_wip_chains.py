# -*- coding: utf-8 -*-
"""Force-rebuild resonance_chain NodeName (ko + _en/_ja/_zhHans) for specific
resonator ids directly from the datamine, bypassing extract_i18n_skills.py's
parity gate.

WHY THIS EXISTS: newly-added (WIP) characters land in the catalog with a STALE
resonance_chain — old-snapshot Korean NodeName that still carries raw UE markup
(<color>, <size>, <te href=…>) and uninterpolated {n} placeholders, and whose
text no longer matches the current datamine. extract_i18n_skills.py's gate
(datamine-ko == catalog-ko after normalization) correctly refuses to localize
these, so they render as broken Korean in every language.

Datamine is the primary catalog source (see datamine-primary-migration), so for
these known-stale ids we TRUST the datamine and rebuild the whole node text from
it: ko is replaced with the interpolated+normalized datamine ko, and _en/_ja/
_zhHans siblings are attached. Alignment is by GroupIndex; a node-count mismatch
(catalog != datamine) SKIPS the character rather than fabricating.

Display-only: the damage engine reads resonance_effects.json (grounded), never
this NodeName text. Only run for ids you have confirmed are stale.

  dry run: python backend/scripts/rebuild_wip_chains.py
  apply  : python backend/scripts/rebuild_wip_chains.py --write
  ids    : python backend/scripts/rebuild_wip_chains.py --ids 1110,1310,1610 --write
Env: DATAMINE_ROOT overrides the datamine location.
"""
import io
import json
import os
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
DM = Path(os.getenv("DATAMINE_ROOT") or (ROOT / "WutheringWaves_Data"))
BIN = DM / "BinData"
CAT = ROOT / "backend" / "data" / "catalog"
LANGS = {"en": "en", "ja": "ja", "zhHans": "zh-Hans"}
WRITE = "--write" in sys.argv

# 3.5 WIP chars whose catalog chain was stale/raw: 수수, 방랑자·전도, 양양·현령.
# (방랑자·회절 1502 has zero datamine RC nodes — no source — so it is not listed.)
DEFAULT_IDS = {1110, 1310, 1610}
if "--ids" in sys.argv:
    raw = sys.argv[sys.argv.index("--ids") + 1]
    TARGET = {int(x) for x in raw.split(",") if x.strip()}
else:
    TARGET = DEFAULT_IDS

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def norm(s):
    return _WS.sub(" ", _TAG.sub("", s or "")).strip()


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


def interp(M, key, params):
    raw = M.get(str(key), "") or ""
    params = params or []

    def sub(m):
        i = int(m.group(1))
        if i < len(params) and params[i] not in (None, ""):
            return str(params[i])
        return m.group(0)

    return re.sub(r"\{(\d+)\}", sub, raw)


MAPS = {"ko": build_map("ko")}
for _suf, _d in LANGS.items():
    MAPS[_suf] = build_map(_d)
ROLEINFO = {d["Id"]: d for d in load_list(BIN / "role/roleinfo.json")}
RC = load_list(BIN / "resonate_chain/resonantchain.json")

res = json.loads((CAT / "resonators.json").read_text(encoding="utf-8"))
changed = 0
for e in res:
    if e.get("id") not in TARGET:
        continue
    ri = ROLEINFO.get(e.get("id"))
    nodes = sorted(
        [r for r in RC if ri and r.get("GroupId") == ri.get("SkillId")],
        key=lambda r: (r.get("GroupIndex") or 0, r.get("Id") or 0),
    )
    chain = e.get("resonance_chain") or []
    print("\n=== %s (id=%s) catalog=%d datamine=%d ==="
          % (e.get("name"), e.get("id"), len(chain), len(nodes)))
    if not chain or len(chain) != len(nodes):
        print("  !! node-count mismatch or empty -> SKIP (no fabrication)")
        continue
    for i, (cn, node) in enumerate(zip(chain, nodes)):
        akey = node.get("AttributesDescription")
        aparams = node.get("AttributesDescriptionParams")
        ko = norm(interp(MAPS["ko"], akey, aparams))
        if not ko:
            print("  S%d: empty datamine ko -> SKIP node" % (i + 1))
            continue
        cn["NodeName"] = ko
        for suf in LANGS:
            v = norm(interp(MAPS[suf], akey, aparams))
            if v:
                cn["NodeName_%s" % suf] = v
        changed += 1
    print("  rebuilt %d nodes (ja set on all)" % len(chain))

print("\ntotal nodes rebuilt: %d" % changed)
if WRITE:
    (CAT / "resonators.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WROTE resonators.json")
else:
    print("DRY RUN (pass --write to apply).")
