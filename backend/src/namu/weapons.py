"""Parse the Namuwiki weapon master table into weapon dicts.

Any weapon-type page (무기/권총 etc.) embeds the same master "무기 유형 및 목록"
table: a grid where rows of 5 icon cells alternate with rows of 5 name cells,
the 5 columns being [대검, 직검, 권총, 권갑, 증폭기], grouped under rarity section
rows ("5성 ...", "4성 ..."). So one fetch yields every weapon.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

_IMG_RE = re.compile(r"namu\.wiki/i/")
WEAPON_TYPES = ["대검", "직검", "권총", "권갑", "증폭기"]


def _cell_icon(cell) -> str | None:
    img = cell.find("img", src=_IMG_RE) or cell.find("img", attrs={"data-src": _IMG_RE})
    if img is None:
        return None
    src = img.get("src") or img.get("data-src") or ""
    if not src:
        return None
    return "https:" + src if src.startswith("//") else src


def _find_master_table(soup: BeautifulSoup):
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        if all(t in text for t in WEAPON_TYPES) and "5성" in text:
            return table
    return None


def parse_weapons(html: str) -> list[dict]:
    """Return [{name_ko, weapon_type, rarity, icon_source}] for every weapon.

    Returns [] if the master table is not found (defensive).
    """
    soup = BeautifulSoup(html, "lxml")
    master = _find_master_table(soup)
    if master is None:
        return []

    rarity: int | None = None
    pending_icons: list[str | None] | None = None
    weapons: list[dict] = []

    for row in master.find_all("tr"):
        cells = row.find_all(["td", "th"])
        text = re.sub(r"\s+", " ", row.get_text(" ", strip=True))
        header = re.match(r"^([1-5])성\s*(.*)$", text)
        if len(cells) <= 2 and header:
            rarity = int(header.group(1))
            pending_icons = None
            continue
        if len(cells) != 5:
            pending_icons = None
            continue
        icons = [_cell_icon(c) for c in cells]
        names = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in cells]
        # In the master grid an icon row has images and no text; a name row has
        # text and no images. Even a single filled column is a real weapon.
        has_icons = any(icons)
        has_names = any(names)
        if has_icons and not any(names):
            pending_icons = icons
        elif pending_icons is not None and has_names and not any(icons):
            for col in range(5):
                if names[col] and pending_icons[col]:
                    weapons.append(
                        {
                            "name_ko": names[col],
                            "weapon_type": WEAPON_TYPES[col],
                            "rarity": rarity,
                            "icon_source": pending_icons[col],
                        }
                    )
            pending_icons = None
        else:
            pending_icons = None
    return weapons
