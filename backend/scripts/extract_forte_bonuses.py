"""Extract each resonator's FIXED forte/skill-tree attribute-bonus totals.

In WuWa every character's forte (resonance skill) tree contains a set of
"attribute bonus" nodes (NodeType==4 in BinData/skillTree/skilltree.json).
When fully unlocked these add a FIXED set of stats to the in-game panel
(+ATK%, +Crit%, +Crit DMG%, +<element> DMG%, +HP%, +DEF%, +Healing%).
Our damage engine currently ignores these, so its computed panel comes out
lower than the in-game panel. This script sums those nodes per resonator and
emits {resonator_id: {statKey: value, ...}} using OUR engine stat-key names,
with percents as plain numbers (e.g. 12.0 == 12%).

Datamine root: DATAMINE_ROOT env override, else <repo>/WutheringWaves_Data.

    backend/.venv/Scripts/python.exe backend/scripts/extract_forte_bonuses.py            # print report
    backend/.venv/Scripts/python.exe backend/scripts/extract_forte_bonuses.py --write    # also write json

Reads only; never mutates the catalog or the engine.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DM = Path(os.getenv("DATAMINE_ROOT") or (REPO / "WutheringWaves_Data"))
BIN = DM / "BinData"

OUT_DEFAULT = Path(r"C:/Users/JungSu/.claude/jobs/5ad2a803/tmp/forte_bonuses.json")

# roleinfo.ElementId -> (element key used in our per-element dmg stat, PropertyIndex id of that element's DMG bonus).
# PropertyIndex ids 22..27 are DamageChangeElement1..6; empirically Id == 21 + ElementId.
ELEMENT_BY_ID = {
    1: ("glacio", 22),   # 응결  Glacio
    2: ("fusion", 23),   # 용융  Fusion
    3: ("electro", 24),  # 전도  Electro
    4: ("aero", 25),     # 기류  Aero
    5: ("spectro", 26),  # 회절  Spectro
    6: ("havoc", 27),    # 인멸  Havoc
}
ELEM_DMG_IDS = {pid: f"{name}Dmg" for name, pid in ELEMENT_BY_ID.values()}

# PropertyIndex.Id -> our engine stat key.  Non-element scalar bonuses.
# (Element DMG ids 22..27 handled via ELEM_DMG_IDS above.)
SCALAR_KEYS = {
    8: "crit",         # Crit Rate    (IsPercent, Value/100)
    9: "critDmg",      # Crit DMG     (IsPercent, Value/100)
    35: "healing",     # Heal Bonus   (IsPercent, Value/100)
    10002: "hpPct",    # GreenLifeMax (IsRatio,   Value*100)
    10007: "atkPct",   # GreenAtk     (IsRatio,   Value*100)
    10010: "defPct",   # GreenDef     (IsRatio,   Value*100)
}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def prop_value(p):
    """Display percentage-points for one skill-tree Property entry.

    Two encodings are used in the datamine (same convention as weapon props):
      IsRatio True  -> Value is a fraction, disp = Value*100  (0.018 -> 1.8)
      IsRatio False -> Value is hundredths-of-a-percent, disp = Value/100 (560 -> 5.6)
    All property ids we consume here are IsPercent, so the False branch is /100.
    """
    return p["Value"] * 100.0 if p.get("IsRatio") else p["Value"] / 100.0


def stat_key_for(pid, element_id):
    if pid in SCALAR_KEYS:
        return SCALAR_KEYS[pid]
    if pid in ELEM_DMG_IDS:
        return ELEM_DMG_IDS[pid]
    return None  # unknown -> caller flags


def extract():
    roleinfo = {r["Id"]: r for r in load_json(BIN / "role/roleinfo.json")}
    tree = load_json(BIN / "skillTree/skilltree.json")
    # SkillTreeGroupId -> role Id (NodeGroup in skilltree keys off SkillTreeGroupId,
    # which usually equals the role id but not always, e.g. Rover 1502 -> group 1501).
    group_to_role = defaultdict(list)
    for rid, ri in roleinfo.items():
        g = ri.get("SkillTreeGroupId")
        if g:
            group_to_role[g].append(rid)

    # attribute-bonus nodes grouped by NodeGroup
    nodes_by_group = defaultdict(list)
    for n in tree:
        if n.get("NodeType") == 4:
            nodes_by_group[n["NodeGroup"]].append(n)

    catalog = load_json(BACKEND / "data/catalog/resonators.json")
    rows = catalog if isinstance(catalog, list) else list(catalog.values())

    result = {}
    diagnostics = []
    for r in rows:
        rid = int(r["id"])
        ri = roleinfo.get(rid)
        if not ri:
            diagnostics.append((rid, r.get("name"), "no roleinfo", {}, []))
            continue
        group = ri.get("SkillTreeGroupId")
        element_id = ri.get("ElementId")
        expect_elem_pid = ELEMENT_BY_ID.get(element_id, (None, None))[1]
        nodes = nodes_by_group.get(group, [])
        totals = defaultdict(float)
        unknown = []
        elem_pids_seen = set()
        for n in nodes:
            for p in n.get("Property", []):
                pid = p["Id"]
                key = stat_key_for(pid, element_id)
                if key is None:
                    unknown.append(pid)
                    continue
                if pid in ELEM_DMG_IDS:
                    elem_pids_seen.add(pid)
                totals[key] += prop_value(p)
        totals = {k: round(v, 2) for k, v in totals.items()}
        result[rid] = totals
        # element sanity: element-dmg node present should match roleinfo element
        elem_ok = (not elem_pids_seen) or (elem_pids_seen == {expect_elem_pid})
        diagnostics.append((rid, r.get("name"), None if (not unknown and elem_ok and len(nodes) == 8) else
                            f"nodes={len(nodes)} unknown={unknown} elem_seen={sorted(elem_pids_seen)} expect={expect_elem_pid}",
                            totals, nodes))
    return result, diagnostics


def main(write):
    result, diags = extract()
    bad = [d for d in diags if d[2]]
    print(f"datamine_root: {DM}")
    print(f"resonators extracted: {len(result)}")
    print(f"flagged (need review): {len(bad)}")
    for rid, name, msg, totals, _ in bad:
        print(f"  ! {rid} {name}: {msg}")
    if write:
        OUT_DEFAULT.parent.mkdir(parents=True, exist_ok=True)
        OUT_DEFAULT.write_text(json.dumps({str(k): v for k, v in sorted(result.items())},
                                          indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"WROTE {OUT_DEFAULT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--write" in sys.argv))
