# -*- coding: utf-8 -*-
"""Phase 2 catalog i18n: add display-only localized names (en / ja / zhHans) to
every catalog entry from the datamine Textmaps. DISPLAY ONLY — the sim engine
keeps the canonical Korean `name`/`name_ko`, so simulation numbers never change.

Sources (datamine multi_text keys, verified by parity gates below):
  resonators -> RoleInfo_<id>_Name          (join by id)
  weapons    -> WeaponConf_<id>_WeaponName   (join by id)
  sonata     -> PhantomFetter_<n>_Name       (join by ko name)
  echoes     -> MonsterInfo_<mid>_Name       (join by ko name, en-parity checked)

Parity gates: an entry is only localized when the datamine KO string matches the
catalog's existing Korean name (and, where a name_en already exists, the datamine
EN matches it). Mismatches/misses are reported and left untouched — never guessed.

Idempotent: adds/refreshes name_en, name_ja, name_zhHans. Never touches name/name_ko.

Usage:
  python backend/scripts/extract_i18n_names.py            # dry run -> report only
  python backend/scripts/extract_i18n_names.py --write    # apply to catalog files
Env: DATAMINE_ROOT overrides the datamine location.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DM = Path(os.getenv("DATAMINE_ROOT") or (ROOT / "WutheringWaves_Data"))
CAT = ROOT / "backend" / "data" / "catalog"
LANGS = {"en": "en", "ja": "ja", "zhHans": "zh-Hans"}  # our field suffix -> datamine textmap dir

WRITE = "--write" in sys.argv


def log(s):
    print(s)


def build_map(lang_dir):
    m = {}
    for half in ("multi_text", "multi_text_1sthalf", "multi_text_2ndhalf"):
        p = DM / "Textmaps" / lang_dir / half / "MultiText.json"
        if p.exists():
            for e in json.loads(p.read_text(encoding="utf-8")):
                if isinstance(e, dict) and "Id" in e:
                    c = e.get("Content") or ""
                    if c or str(e["Id"]) not in m:
                        m[str(e["Id"])] = c
    return m


def load(name):
    return json.loads((CAT / name).read_text(encoding="utf-8"))


# The catalog files were serialized inconsistently by earlier tooling, so match
# each file's existing style exactly (indent + trailing newline) — otherwise a
# whole-file reformat swamps the real "+name_ja/+name_zhHans" diff.
FORMATS = {
    "resonators.json": (2, True),
    "weapons.json": (2, False),
    "echoes.json": (2, True),
    "sonata_sets.json": (None, False),
}


def save(name, data):
    indent, nl = FORMATS[name]
    text = json.dumps(data, ensure_ascii=False, indent=indent)
    (CAT / name).write_text(text + ("\n" if nl else ""), encoding="utf-8")


log("datamine: %s" % DM)
MAPS = {"ko": build_map("ko")}
for suf, d in LANGS.items():
    MAPS[suf] = build_map(d)
log("map sizes: " + ", ".join("%s=%d" % (k, len(v)) for k, v in MAPS.items()))


def localize(cat_name, catalog, ko_field, key_for):
    """Generic id-keyed localizer. key_for(entry)->textmap key. Parity: ko match.

    Fallback: if the datamine KO differs from the catalog KO but the catalog
    already has a name_en that equals the datamine EN, trust the row (covers the
    Rover 1502 case where datamine KO is the bare '방랑자' yet EN/JA/ZH carry the
    element suffix, matching our catalog's 'Rover: Spectro')."""
    ok = miss = mismatch = 0
    for e in catalog:
        key = key_for(e)
        ko = MAPS["ko"].get(key)
        cat_ko = e.get(ko_field)
        if ko is None:
            miss += 1
            log("  MISS  %s id=%s key=%s (no datamine ko)" % (cat_name, e.get("id"), key))
            continue
        if ko != cat_ko:
            en = MAPS["en"].get(key)
            if e.get("name_en") and en and en == e["name_en"]:
                log("  KO-DIFF-EN-OK %s id=%s: datamine.ko=%r catalog.ko=%r (en=%r matches)" % (cat_name, e.get("id"), ko, cat_ko, en))
            else:
                mismatch += 1
                log("  KO-MISMATCH %s id=%s: datamine=%r catalog=%r" % (cat_name, e.get("id"), ko, cat_ko))
                continue
        for suf in LANGS:
            val = MAPS[suf].get(key) or ""
            if suf == "en" and e.get("name_en") and val and val != e["name_en"]:
                log("  EN-DIFF %s id=%s: datamine=%r catalog=%r (keeping datamine)" % (cat_name, e.get("id"), val, e["name_en"]))
            if val:
                e["name_%s" % suf] = val
        ok += 1
    log("%s: ok=%d miss=%d ko-mismatch=%d / %d" % (cat_name, ok, miss, mismatch, len(catalog)))
    return ok


def build_ko_index(prefix):
    """ko string -> textmap key, restricted to keys starting with `prefix`.
    When a ko string maps to several keys (e.g. a two-phase boss echo like
    Hecate), keep it only if every target language agrees across those keys;
    then any one key is safe to use. Genuinely conflicting duplicates are
    dropped and reported as misses."""
    from collections import defaultdict
    idx = defaultdict(set)
    for k, v in MAPS["ko"].items():
        if k.startswith(prefix) and v:
            idx[v].add(k)
    out = {}
    for v, ks in idx.items():
        if len(ks) == 1:
            out[v] = next(iter(ks))
            continue
        agree = True
        for suf in LANGS:
            vals = {MAPS[suf].get(k) for k in ks if MAPS[suf].get(k)}
            if len(vals) > 1:
                agree = False
                break
        if agree:
            out[v] = next(iter(ks))
    return out


def localize_by_ko(cat_name, catalog, ko_field, prefix):
    """Join by ko name against a prefixed key index; en-parity where available."""
    idx = build_ko_index(prefix)
    ok = miss = 0
    for e in catalog:
        cat_ko = e.get(ko_field)
        key = idx.get(cat_ko)
        if not key:
            miss += 1
            log("  MISS  %s id=%s ko=%r (no unique %s* key)" % (cat_name, e.get("id"), cat_ko, prefix))
            continue
        for suf in LANGS:
            val = MAPS[suf].get(key) or ""
            if suf == "en" and e.get("name_en") and val and val != e["name_en"]:
                log("  EN-DIFF %s id=%s: datamine=%r catalog=%r (keeping datamine)" % (cat_name, e.get("id"), val, e["name_en"]))
            if val:
                e["name_%s" % suf] = val
        ok += 1
    log("%s: ok=%d miss=%d / %d" % (cat_name, ok, miss, len(catalog)))
    return ok


# --- resonators (ko field = 'name') ---
res = load("resonators.json")
localize("resonators", res, "name", lambda e: "RoleInfo_%s_Name" % e["id"])

# --- weapons (ko field = 'name_ko') ---
wp = load("weapons.json")
localize("weapons", wp, "name_ko", lambda e: "WeaponConf_%s_WeaponName" % e["id"])

# --- sonata sets (ko field = 'name_ko', join by ko) ---
ss = load("sonata_sets.json")
localize_by_ko("sonata_sets", ss, "name_ko", "PhantomFetter_")

# --- echoes (ko field = 'name_ko', join by ko) ---
ec = load("echoes.json")
localize_by_ko("echoes", ec, "name_ko", "MonsterInfo_")

if WRITE:
    save("resonators.json", res)
    save("weapons.json", wp)
    save("sonata_sets.json", ss)
    save("echoes.json", ec)
    log("WROTE catalog files.")
else:
    log("DRY RUN (pass --write to apply).")
