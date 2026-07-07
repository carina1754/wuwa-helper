"""Map encore.moe detail records into our stored data_json schema.

Field names mirror what the frontend codex already reads (SkillName/SkillDescribe,
resonance_chain strings, weapon desc, echo skill{DescriptionEx,SkillCD}) so the
existing UI keeps rendering, plus per-level ``stat_curves`` / weapon ``properties``
curves so the codex / builder can show values at any level or rank via a slider.
"""
from __future__ import annotations

import re

# encore Property.Name (ko) -> our canonical stat key
_CHAR_STAT_KEY = {
    "HP": "Life",
    "공격력": "Atk",
    "방어력": "Def",
    "크리티컬": "Crit",
    "크리티컬 피해": "CritDamage",
}
# echo rarity (0-3) -> cost, consistent with WuWa (cost1/3/4)
_ECHO_RARITY_COST = {0: 1, 1: 3, 2: 4, 3: 4}
_TAG_RE = re.compile(r"<[^>]+>")


def _num(value):
    """Parse a stat value that may be a number or a percent string like '5%'."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        s = value.strip().replace("%", "")
        try:
            return float(s)
        except ValueError:
            return value
    return value


def strip_tags(text):
    return _TAG_RE.sub("", text or "").strip() if text else ""


def _content(node):
    return node.get("Content") if isinstance(node, dict) else node


def _curve(growth):
    return [
        {"level": g.get("level") or g.get("Level"), "value": _num(g.get("value") or g.get("Value"))}
        for g in (growth or [])
    ]


def normalize_resonator(d: dict, name_en: str | None = None) -> dict:
    curves: dict[str, list] = {}
    stats: dict[str, float] = {}
    for p in d.get("Properties", []):
        key = _CHAR_STAT_KEY.get(p.get("Name"))
        if not key:
            continue
        curve = _curve(p.get("GrowthValues"))
        curves[key] = curve
        if curve:
            stats[key] = curve[-1]["value"]
    skills = [
        {
            "SkillName": strip_tags(s.get("SkillName")),
            "SkillDescribe": s.get("SkillDescribe"),  # keep tags; frontend strips
            "SkillType": s.get("SkillType"),
            "Icon": s.get("Icon"),
        }
        for s in d.get("Skills", [])
    ]
    chain = [
        strip_tags(c.get("AttributesDescription")) or strip_tags(c.get("NodeName"))
        for c in d.get("ResonantChain", [])
    ]
    return {
        "id": d.get("Id"),
        "name": _content(d.get("Name")),
        "name_en": name_en,
        "nickname": _content(d.get("NickName")),
        "rarity": d.get("QualityId"),
        "element": d.get("ElementName"),
        "weapon_type": d.get("WeaponTypeName"),
        "weapon_type_ko": d.get("WeaponTypeName"),
        "image": d.get("RoleHeadIcon"),
        "introduction": strip_tags(_content(d.get("Introduction"))),
        "skills": skills,
        "resonance_chain": chain,
        "stats": stats,
        "stat_curves": curves,
        "max_level": d.get("MaxLevel", 90),
        "source": "encore.moe",
    }


def normalize_weapon(d: dict, name_en: str | None = None) -> dict:
    props = []
    for p in d.get("Properties", []):
        curve = _curve(p.get("GrowthValues"))
        props.append(
            {
                "name": p.get("Name"),
                "base": p.get("BaseValue"),
                "curve": curve,
                "max": curve[-1]["value"] if curve else None,
            }
        )
    return {
        "id": d.get("ItemId"),
        "name_ko": d.get("WeaponName"),
        "name_en": name_en,
        "rarity": d.get("QualityId"),
        "weapon_type": d.get("WeaponType"),
        "desc": d.get("Desc"),  # rank-scaled passive; tags kept, frontend strips
        "attributes_description": strip_tags(d.get("AttributesDescription")),
        "resonance": None,
        "properties": props,  # per-level curves for the slider (main ATK + sub-stat)
        "icon": d.get("Icon") or d.get("IconMiddle"),
        "source": "encore.moe",
    }


def normalize_echo(d: dict, name_en: str | None = None) -> dict:
    rarity = d.get("Rarity")
    sonata = []
    for fg in d.get("FetterGroupDetails", []) or []:
        grp = fg.get("Group") if isinstance(fg, dict) else None
        name = (grp or {}).get("FetterGroupName") if grp else None
        if name and strip_tags(name) not in sonata:
            sonata.append(strip_tags(name))
    if not sonata:
        for fg in d.get("FetterGroup", []) or []:
            n = fg.get("FetterGroupName") if isinstance(fg, dict) else None
            if n and strip_tags(n) not in sonata:
                sonata.append(strip_tags(n))
    skill = d.get("Skill") or {}
    return {
        "id": d.get("ItemId") or d.get("MonsterId"),
        "name_ko": d.get("MonsterName"),
        "name_en": name_en,
        "rarity": rarity,
        "cost": _ECHO_RARITY_COST.get(rarity),
        "element": (d.get("Element") or {}).get("Name") if isinstance(d.get("Element"), dict) else None,
        "phantom_type": d.get("PhantomType"),
        "sonata": sonata,
        "main_prop": d.get("MainProp"),
        "skill": {"DescriptionEx": skill.get("DescriptionEx"), "SkillCD": skill.get("SkillCD")} if skill else None,
        "icon": d.get("IconMiddle") or d.get("Icon"),
        "source": "encore.moe",
    }
