"""Extract Wuthering Waves echoes from the local datamine into our catalog schema.

Reusable, parity-gated extractor. Given a phantomitem ItemId it reproduces the
exact `backend/data/catalog/echoes.json` object shape from the datamine
(ResVer 3.5.5 clone at repo/WutheringWaves_Data).

Field derivations (learned from the existing 245 catalog entries):
  id            = phantomitem.ItemId
  name_ko       = MultiText[ko][ MonsterName ]
  name_en       = MultiText[en][ MonsterName ]
  rarity        = phantomitem.Rarity          (0..3)
  cost          = {0:1, 1:3, 2:4, 3:4}[Rarity]
  element       = ELEM_MAP[ ElementType[0] ]
  phantom_type  = phantomitem.PhantomType     (1 normal / 2 aberration-boss)
  sonata        = [ MultiText[ko][ fetterGroup.FetterGroupName ] for id in FetterGroup ]
  main_prop     = phantomitem.MainProp        ({RandGroupId, RandNum})
  skill.DescriptionEx = render( MultiText[ko][ phantomskill.DescriptionEx ],
                                phantomskill.LevelDescStrArray[-1] )  # max level, \n -> <br>
  skill.SkillCD = phantomskill.SkillCD
  icon          = /catalog/image/echoes/<ItemId>
  source        = "encore.moe"
  sim_source    = given (datamine-3.5.0 for existing / datamine-3.5.5 for new)

name_en is the ONLY field that leaves the datamine: it comes from the English
MultiText for the same MonsterName key (present in the local clone), so it is
fully reproducible here.
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DM = os.path.join(REPO, "WutheringWaves_Data")
PHANTOM = os.path.join(DM, "BinData", "phantom")
CATALOG = os.path.join(REPO, "backend", "data", "catalog", "echoes.json")

ELEM_MAP = {0: "물리", 1: "응결", 2: "용융", 3: "전도", 4: "기류", 5: "회절", 6: "인멸"}
COST_MAP = {0: 1, 1: 3, 2: 4, 3: 4}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_textmap(lang):
    p = os.path.join(DM, "Textmaps", lang, "multi_text", "MultiText.json")
    return {r["Id"]: r["Content"] for r in _load(p)}


class Extractor:
    def __init__(self):
        self.item = {r["ItemId"]: r for r in _load(os.path.join(PHANTOM, "phantomitem.json"))}
        self.skill = {r["PhantomSkillId"]: r for r in _load(os.path.join(PHANTOM, "phantomskill.json"))}
        self.fetter = {r["Id"]: r for r in _load(os.path.join(PHANTOM, "phantomfettergroup.json"))}
        self.ko = _load_textmap("ko")
        self.en = _load_textmap("en")

    def render_skill(self, sk):
        template = self.ko.get(sk["DescriptionEx"], "")
        lvls = sk.get("LevelDescStrArray") or []
        args = lvls[-1]["ArrayString"] if lvls else []
        out = template.replace("\n", "<br>")
        # placeholders are {0},{1},... filled from the MAX-level ArrayString
        def repl(m):
            i = int(m.group(1))
            return args[i] if i < len(args) else m.group(0)
        out = re.sub(r"\{(\d+)\}", repl, out)
        return out

    def extract(self, item_id, sim_source="datamine-3.5.5"):
        r = self.item[item_id]
        sk = self.skill[r["SkillId"]]
        sonata = [self.ko.get(self.fetter[f]["FetterGroupName"]) for f in r["FetterGroup"]]
        return {
            "id": r["ItemId"],
            "name_ko": self.ko.get(r["MonsterName"]),
            "name_en": self.en.get(r["MonsterName"]),
            "rarity": r["Rarity"],
            "cost": COST_MAP[r["Rarity"]],
            "element": ELEM_MAP[r["ElementType"][0]],
            "phantom_type": r["PhantomType"],
            "sonata": sonata,
            "main_prop": {"RandGroupId": r["MainProp"]["RandGroupId"], "RandNum": r["MainProp"]["RandNum"]},
            "skill": {"DescriptionEx": self.render_skill(sk), "SkillCD": sk["SkillCD"]},
            "icon": f"/catalog/image/echoes/{r['ItemId']}",
            "source": "encore.moe",
            "sim_source": sim_source,
        }


# ---------------------------------------------------------------------------
FIELDS = ["name_ko", "name_en", "rarity", "cost", "element", "phantom_type",
          "sonata", "main_prop"]


def parity_gate(ex, sample_ids):
    catalog = {e["id"]: e for e in _load(CATALOG)}
    scores = {f: 0 for f in FIELDS}
    scores["skill.DescriptionEx"] = 0
    scores["skill.SkillCD"] = 0
    n = 0
    mismatches = []
    for iid in sample_ids:
        if iid not in catalog:
            continue
        n += 1
        got = ex.extract(iid, sim_source=catalog[iid].get("sim_source", "datamine-3.5.0"))
        exp = catalog[iid]
        for f in FIELDS:
            if got[f] == exp[f]:
                scores[f] += 1
            else:
                mismatches.append((iid, f, got[f], exp[f]))
        for sf in ("DescriptionEx", "SkillCD"):
            if got["skill"][sf] == exp["skill"][sf]:
                scores["skill." + sf] += 1
            else:
                mismatches.append((iid, "skill." + sf, got["skill"][sf], exp["skill"][sf]))
    return n, scores, mismatches


if __name__ == "__main__":
    ex = Extractor()
    catalog = _load(CATALOG)
    all_ids = [e["id"] for e in catalog]

    # ---- parity sample: spread across cost 1/3/4, PT1/PT2, both main_prop families
    byid = {e["id"]: e for e in catalog}
    def pick(pred, k):
        return [e["id"] for e in catalog if pred(e)][:k]
    sample = []
    sample += pick(lambda e: e["cost"] == 1 and e["main_prop"]["RandGroupId"] // 100 == 5, 8)
    sample += pick(lambda e: e["cost"] == 3 and e["main_prop"]["RandGroupId"] // 100 == 5, 7)
    sample += pick(lambda e: e["cost"] == 4 and e["main_prop"]["RandGroupId"] // 100 == 5, 7)
    sample += pick(lambda e: e["main_prop"]["RandGroupId"] // 100 == 2, 5)   # 20x family
    sample += pick(lambda e: e["phantom_type"] == 2, 5)                       # aberration/boss
    sample = list(dict.fromkeys(sample))[:30]

    n, scores, mismatches = parity_gate(ex, sample)
    print(f"PARITY GATE over {n} existing echoes:")
    for f, s in scores.items():
        print(f"  {f:22s} {s}/{n}")
    if mismatches:
        print(f"\n{len(mismatches)} field mismatches:")
        for iid, f, got, exp in mismatches[:40]:
            print(f"  {iid} {f}\n    got={got!r}\n    exp={exp!r}")
    else:
        print("\nALL FIELDS 100% PARITY")
