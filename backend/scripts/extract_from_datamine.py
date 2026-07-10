"""VERIFIED extractor core: build catalog-shaped skills[] for a role from datamine
via skill.json DamageList -> damage.json RateLv. Reusable; parity_v2 imports it."""
import json
import sys
from collections import defaultdict
from pathlib import Path

DM = Path(r"C:\Users\JungSu\Desktop\wawa-ai-coach\WutheringWaves_Data-3.5")
BIN = DM / "BinData"


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


KO = build_map("ko")
EN = build_map("en")
SKILLTYPE_KO = {r["Id"]: KO.get(str(r.get("TypeName")), "") for r in load_list(BIN / "skill/skilltype.json")}
ROLEINFO = {d["Id"]: d for d in load_list(BIN / "role/roleinfo.json")}
_SK = load_list(BIN / "skill/skill.json")
SKILLS_BY_GROUP = defaultdict(list)
for s in _SK:
    SKILLS_BY_GROUP[s.get("SkillGroupId")].append(s)
DMG = {d.get("Id"): d for d in load_list(BIN / "damage/damage.json")}
BP1 = {r.get("Id"): r for r in load_list(BIN / "property/baseproperty.json") if r.get("Lv") == 1}
GROWTH = sorted(load_list(BIN / "property/rolepropertygrowth.json"), key=lambda r: r.get("Id") or 0)


def _round(x):
    return round(x, 4)


WC = {w.get("ItemId"): w for w in load_list(BIN / "weapon/weaponconf.json")}
PROPIDX = {r.get("Id"): r for r in load_list(BIN / "property/propertyindex.json")}
_WG = load_list(BIN / "property/weaponpropertygrowth.json")
WGROWTH = defaultdict(list)
for r in sorted(_WG, key=lambda x: x.get("Id") or 0):
    WGROWTH[r.get("CurveId")].append(r)
WTYPE_KO = {1: "광검", 2: "직검", 3: "권갑", 4: "권총", 5: "증폭기"}
WTYPE_EN = {1: "Broadblade", 2: "Sword", 3: "Gauntlets", 4: "Pistols", 5: "Rectifier"}


def build_weapon_properties(wid):
    """[{name,base,curve:[{level,value}]}] for weapon ItemId `wid`."""
    w = WC.get(wid)
    if not w:
        return None
    props = []
    for slot, ckey in (("FirstPropId", "FirstCurve"), ("SecondPropId", "SecondCurve")):
        p = w.get(slot)
        if not isinstance(p, dict) or not p.get("Id"):
            continue
        pid = p.get("Id")
        pidx = PROPIDX.get(pid) or {}
        val = p.get("Value") or 0
        if p.get("IsRatio"):
            disp = val * 100.0            # 0.081 -> 8.1 (percentage points)
        elif pidx.get("IsPercent"):
            disp = val / 100.0            # 540 -> 5.4
        else:
            disp = val                    # 47 -> 47 (flat)
        name = KO.get(str(pidx.get("Name")), "")
        cid = w.get(ckey)
        curve = [{"level": g.get("Level"), "value": round(disp * (g.get("CurveValue") or 0) / 10000.0, 2)}
                 for g in WGROWTH.get(cid, [])]
        props.append({"name": name, "base": val, "curve": curve})
    return props


def build_weapon_desc(wid):
    """catalog `desc`: KO Desc template with {i} -> '/'.join(DescParams[i].ArrayString)."""
    wc = WC.get(wid)
    if not wc:
        return None
    raw = KO.get(str(wc.get("Desc")), "")
    params = wc.get("DescParams") or []

    def sub(m):
        i = int(m.group(1))
        if i < len(params) and isinstance(params[i], dict):
            arr = params[i].get("ArrayString")
            if arr:
                return "/".join(str(x) for x in arr)
        return m.group(0)

    import re as _re
    return _re.sub(r"\{(\d+)\}", sub, raw)


def build_weapon_attr(wid):
    """catalog `attributes_description` (lore) from WeaponConf_<id>_AttributesDescription."""
    wc = WC.get(wid)
    if not wc:
        return None
    return KO.get(str(wc.get("AttributesDescription")), "")


def build_stat_curves(rid):
    """{Life,Atk,Def,Crit,CritDamage: [{level,value}]} via baseLv1 x growth ratio/1e4."""
    ri = ROLEINFO.get(rid)
    if not ri:
        return None
    b = BP1.get(ri.get("PropertyId") or rid) or BP1.get(rid)
    if not b:
        return None
    life0, atk0, def0 = b.get("LifeMax") or b.get("Life"), b.get("Atk"), b.get("Def")
    crit = (b.get("Crit") or 0) / 100.0
    critdmg = (b.get("CritDamage") or 0) / 100.0
    life, atk, dfn, cr, cd = [], [], [], [], []
    for g in GROWTH:
        lv = g.get("Level")
        life.append({"level": lv, "value": _round(life0 * (g.get("LifeMaxRatio") or 0) / 10000.0)})
        atk.append({"level": lv, "value": _round(atk0 * (g.get("AtkRatio") or 0) / 10000.0)})
        dfn.append({"level": lv, "value": _round(def0 * (g.get("DefRatio") or 0) / 10000.0)})
        cr.append({"level": lv, "value": crit})
        cd.append({"level": lv, "value": critdmg})
    return {"Life": life, "Atk": atk, "Def": dfn, "Crit": cr, "CritDamage": cd}


def _fmt(v):
    r = v / 100.0
    return ("%f" % r).rstrip("0").rstrip(".") + "%"


def damage_rates(damage_id, maxlv):
    """Per-level rate strings for one DamageList id, or None to skip."""
    e = DMG.get(damage_id)
    if e is None:
        return None
    if e.get("Condition"):        # conditional variant -> 0% (avoid double count)
        return ["0%"]
    rl = e.get("RateLv")
    if not isinstance(rl, list) or not rl:
        return None
    n = max(1, min(maxlv or 1, len(rl)))
    return [_fmt(rl[i]) for i in range(n)]


def build_skills(rid):
    """Return catalog-shaped skills[] for role id `rid`."""
    ri = ROLEINFO.get(rid)
    if not ri:
        return None
    out = []
    rows = SKILLS_BY_GROUP.get(ri.get("SkillId"), [])
    for sk in sorted(rows, key=lambda x: (x.get("SortIndex") or 0, x.get("Id") or 0)):
        label = SKILLTYPE_KO.get(sk.get("SkillType"), "")
        M = sk.get("MaxSkillLevel") or 1
        dmgs = []
        for did in (sk.get("DamageList") or []):
            rates = damage_rates(did, M)
            if rates is None:
                continue
            dmgs.append({"name": label, "rates": rates})
        out.append({
            "SkillName": KO.get(str(sk.get("SkillName")), "") or KO.get(str(sk.get("Name")), ""),
            "SkillType": label,
            "SkillDescribe": KO.get(str(sk.get("SkillDescribe")), ""),
            "damage": dmgs,
        })
    return out


if __name__ == "__main__":
    import io
    import pprint
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    pprint.pprint(build_skills(1208))
