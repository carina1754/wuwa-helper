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
