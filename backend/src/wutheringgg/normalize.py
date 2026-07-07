"""Normalize raw wuthering.gg records into our schema; derive image URLs."""
from __future__ import annotations

WEAPON_TYPE: dict[int, tuple[str, str]] = {
    1: ("Broadsword", "대검"),
    2: ("Sword", "직검"),
    3: ("Pistols", "권총"),
    4: ("Gauntlets", "권갑"),
    5: ("Rectifier", "증폭기"),
}


def image_url(category: str, asset: str) -> str:
    return f"https://wuthering.gg/images/{category}/{asset}"


def _element_name(raw_element: object) -> str | None:
    """The live KO ``Element`` field is a ``{Id, Name, Icon7}`` object; older or
    other builds may carry a bare string. Return the localized element name."""
    if isinstance(raw_element, dict):
        return raw_element.get("Name")
    return raw_element  # already a string (or None)


def normalize_character(raw: dict) -> dict:
    wt = WEAPON_TYPE.get(raw.get("WeaponType"), ("", ""))
    return {
        "id": raw["Id"],
        "name": raw.get("Name"),
        "name_en": raw.get("NameEn"),
        "rarity": raw.get("QualityId"),
        "element": _element_name(raw.get("Element")),
        "weapon_type": wt[0],
        "weapon_type_ko": wt[1],
        "role_type": raw.get("RoleType"),
        "head_icon_asset": raw.get("RoleHeadIconBig"),
        "skills": raw.get("Skills") or [],
        "resonance_chain": raw.get("ResonantChainGroup") or [],
        "ascension": raw.get("Ascension") or [],
        "stats": raw.get("Stats") or {},
        "introduction": raw.get("Introduction"),
    }


def normalize_weapon(raw: dict) -> dict:
    """Normalize a live weapon record. Live keys: Id, WeaponName, WeaponNameEn,
    WeaponType, QualityId, Icon, Desc, AttributesDescription, TypeDescription,
    Resonance, Ascension, First/SecondPropId, First/SecondCurve, DescParams."""
    wt = WEAPON_TYPE.get(raw.get("WeaponType"), ("", ""))
    return {
        # weapon_catalog.id is TEXT; store the game Id as a string.
        "id": str(raw["Id"]),
        "name_ko": raw.get("WeaponName"),
        "name_en": raw.get("WeaponNameEn"),
        "weapon_type": wt[0],
        "weapon_type_ko": wt[1],
        "rarity": raw.get("QualityId"),
        "icon_asset": raw.get("Icon"),
        "desc": raw.get("Desc"),
        "attributes_description": raw.get("AttributesDescription"),
        "type_description": raw.get("TypeDescription"),
        "resonance": raw.get("Resonance") or [],
        "ascension": raw.get("Ascension") or [],
    }


def _sonata_names(fetter_group: object) -> list[str]:
    """An echo's Sonata set names live in FetterGroup[].FetterGroupName."""
    names: list[str] = []
    if isinstance(fetter_group, list):
        for g in fetter_group:
            if isinstance(g, dict) and g.get("FetterGroupName"):
                names.append(g["FetterGroupName"])
    return names


def normalize_echo(raw: dict) -> dict:
    """Normalize a live echo (phantom) record. Live keys: Id, MonsterName,
    MonsterNameEn, Cost, QualityId, Rarity, Rare, PhantomType, IconMiddle,
    IconBig, Skill, MainProp, Desc, FetterGroup, LevelUpGroupId, PolishCost,
    ParentMonsterId. IconMiddle is a usable PNG filename; IconBig is a raw UE
    asset path, so we cache from IconMiddle."""
    return {
        # echo_catalog.id is TEXT; store the game Id as a string.
        "id": str(raw["Id"]),
        "name_ko": raw.get("MonsterName"),
        "name_en": raw.get("MonsterNameEn"),
        "cost": raw.get("Cost"),
        "rarity": raw.get("QualityId"),
        "phantom_type": raw.get("PhantomType"),
        "icon_asset": raw.get("IconMiddle"),
        "sonata": _sonata_names(raw.get("FetterGroup")),
        "skill": raw.get("Skill"),
        "main_prop": raw.get("MainProp"),
        "desc": raw.get("Desc"),
    }
