"""Namuwiki character-page parser for Wuthering Waves (명조: 워더링 웨이브).

Exposes: parse_character(html: str) -> dict

Design notes
------------
Namuwiki's server-rendered markup lays every top-level content block (headings,
paragraphs, tables) as flat siblings under one wrapper div. Concretely, for any
heading element `h`, `h.parent.parent.parent` reaches that flat container, and
its element children (in document order) are the "blocks" of the article:
headings (h1/h2/h3/h4) interleaved with content blocks (div/table wrappers).

The parser locates a heading by matching its visible text (ignoring the
trailing "[편집]" edit-link text and leading numbering like "3.2."), then
walks forward through sibling blocks until the next heading whose tag level
is <= the current heading's level (i.e., until the section ends), collecting
whatever tables/lists live in between.

Everything is defensive: any missing section/table/pattern results in an
omitted or empty field, never a crash.
"""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
_CHAR_LINK_RE = re.compile(r"^(.*?)\(명조: 워더링 웨이브\)$")


# ---------------------------------------------------------------------------
# Flat block-list helpers
# ---------------------------------------------------------------------------

def _flat_container(heading: Tag) -> Optional[Tag]:
    """Climb from a heading to the ancestor div that holds all top-level blocks."""
    node = heading
    for _ in range(3):
        if node.parent is None:
            return None
        node = node.parent
    return node


def _blocks(soup: BeautifulSoup) -> list[Tag]:
    """Return the flat list of top-level content blocks (headings + content divs).

    The page's <h1> title lives in a separate small header area, so we anchor
    on the first <h2> (article body sections always start with "1.개요") to
    find the real flat content container.
    """
    first_heading = soup.find("h2")
    if first_heading is None:
        return []
    container = _flat_container(first_heading)
    if container is None:
        return []
    blocks = [c for c in container.children if isinstance(c, Tag)]
    # Sanity check: the container should hold many blocks (article body).
    # If not, fall back to searching ancestors for a larger sibling list.
    node = container
    tries = 0
    while len(blocks) < 10 and node.parent is not None and tries < 5:
        node = node.parent
        blocks = [c for c in node.children if isinstance(c, Tag)]
        tries += 1
    return blocks


def _heading_info(block: Tag) -> Optional[tuple[int, str, Tag]]:
    """If block contains/is a heading, return (level, clean_text, heading_tag)."""
    h = block if block.name in _HEADING_TAGS else block.find(_HEADING_TAGS)
    if h is None:
        return None
    level = int(h.name[1])
    text = h.get_text(" ", strip=True)
    text = text.replace("[편집]", "").strip()
    # strip leading numbering like "3.2." or "3.2.1."
    text = re.sub(r"^[\d.]+\s*", "", text)
    return level, text, h


def _find_section(blocks: list[Tag], text_frag: str) -> Optional[tuple[int, int]]:
    """Find a section whose heading text matches text_frag.

    Prefers an exact match of the (cleaned) heading text to text_frag; if none
    exists, falls back to a substring match. This avoids e.g. "스킬" matching
    "스킬 업그레이드" when the real target is a heading titled exactly "스킬".

    Returns (start_idx, end_idx) where blocks[start_idx] is the heading block
    and blocks[start_idx+1:end_idx] are the section's content blocks (end_idx
    exclusive), stopping at the next heading of level <= this heading's level.
    """
    def _make_span(i: int, level: int) -> tuple[int, int]:
        end = len(blocks)
        for j in range(i + 1, len(blocks)):
            info2 = _heading_info(blocks[j])
            if info2 is not None and info2[0] <= level:
                end = j
                break
        return i, end

    substring_hit = None
    for i, b in enumerate(blocks):
        info = _heading_info(b)
        if info is None:
            continue
        level, text, _ = info
        if text == text_frag:
            return _make_span(i, level)
        if substring_hit is None and text_frag in text:
            substring_hit = (i, level)
    if substring_hit is not None:
        return _make_span(*substring_hit)
    return None


def _section_blocks(blocks: list[Tag], text_frag: str) -> list[Tag]:
    span = _find_section(blocks, text_frag)
    if span is None:
        return []
    start, end = span
    return blocks[start + 1:end]


def _subsections(blocks: list[Tag], text_frag: str, sub_level: Optional[int] = None):
    """Yield (subsection_title, content_blocks) for each heading found directly
    within the named section, at the first heading level encountered inside it
    (or `sub_level` if given)."""
    span = _find_section(blocks, text_frag)
    if span is None:
        return
    start, end = span
    parent_level = _heading_info(blocks[start])[0]
    section = blocks[start + 1:end]

    # Determine the level of subsection headings (first heading found).
    target_level = sub_level
    if target_level is None:
        for b in section:
            info = _heading_info(b)
            if info is not None:
                target_level = info[0]
                break
    if target_level is None:
        return

    cur_title = None
    cur_blocks: list[Tag] = []
    for b in section:
        info = _heading_info(b)
        if info is not None and info[0] == target_level:
            if cur_title is not None:
                yield cur_title, cur_blocks
            cur_title = info[1]
            cur_blocks = []
        elif info is not None and info[0] < target_level:
            # left the subsection scope entirely (shouldn't normally happen
            # since _section_blocks already bounds by parent_level)
            break
        else:
            cur_blocks.append(b)
    if cur_title is not None:
        yield cur_title, cur_blocks


def _text(tag: Optional[Tag], sep: str = " ") -> str:
    if tag is None:
        return ""
    return tag.get_text(sep, strip=True)


def _first_table(blocks: list[Tag]) -> Optional[Tag]:
    for b in blocks:
        t = b.find("table") if b.name != "table" else b
        if t is not None:
            return t
    return None


def _all_tables(blocks: list[Tag]) -> list[Tag]:
    tables = []
    for b in blocks:
        tables.extend(b.find_all("table"))
    return tables


# ---------------------------------------------------------------------------
# Basic info
# ---------------------------------------------------------------------------

def _parse_basic_info(soup: BeautifulSoup, blocks: list[Tag]) -> dict:
    info: dict = {
        "name_ko": None,
        "name_alt": {},
        "element": None,
        "weapon_type": None,
        "faction": None,
        "gender": None,
        "birthday": None,
        "birthplace": None,
        "resonance_ability": None,
        "rarity": None,
    }

    h1 = soup.find("h1")
    if h1:
        name = h1.get_text(strip=True)
        m = _CHAR_LINK_RE.match(name)
        info["name_ko"] = m.group(1) if m else name

    # The character infobox is the first sizeable table appearing before "1.개요".
    span = _find_section(blocks, "개요")
    infobox_table = None
    if span is not None:
        start = span[0]
        for b in blocks[:start]:
            t = b.find("table") if b.name != "table" else b
            if t is not None and re.search(r"속성\s*:\s*\S", t.get_text()):
                infobox_table = t
                break
    if infobox_table is not None:
        txt = infobox_table.get_text(" | ", strip=True)
        for key, field in (
            ("성별", "gender"),
            ("생일", "birthday"),
            ("속성", "element"),
            ("무기", "weapon_type"),
            ("세력", "faction"),
            ("출생", "birthplace"),
        ):
            m = re.search(re.escape(key) + r"\s*:\s*([^|]+)", txt)
            if m:
                info[field] = m.group(1).strip()
        m = re.search(r"공명 어빌리티\s*:\s*([^|]+)", txt)
        if m:
            info["resonance_ability"] = m.group(1).strip()

    # Rarity: search the "평가" (evaluation) intro paragraph, which routinely
    # states things like "2.0 버전에 출시된 최초의 5성 한정 인멸 속성 서브 딜러".
    # Avoid the page-wide ToC/weapon-section headings ("6.2.1. 5성"), which
    # describe weapon rarity tiers, not the character's own rarity.
    eval_span = _find_section(blocks, "평가")
    if eval_span is not None:
        eval_text = " ".join(
            b.get_text(" ", strip=True) for b in blocks[eval_span[0] + 1:eval_span[1]]
        )
        m = re.search(r"([45])성(?!\s*\[편집\])", eval_text)
        if m:
            info["rarity"] = int(m.group(1))

    return info


# ---------------------------------------------------------------------------
# Skills (3.2)
# ---------------------------------------------------------------------------

_SKILL_LEVEL_ROW_HINTS = (
    "피해", "스태미나", "소모", "회복", "쿨타임", "지속", "확률", "배율",
)


_SKILL_SLOT_LABELS = (
    "기본 공격", "공명 스킬", "공명 회로", "공명 해방",
    "변주 스킬", "반주 스킬", "조화도 파괴",
)


def _extract_max_level_value(value_text: str) -> Optional[str]:
    """From a '~ 10 values separated by spaces' cell, return the last (max lvl) token."""
    tokens = value_text.split()
    if not tokens:
        return None
    return tokens[-1]


def _parse_skill_table(table: Tag) -> dict:
    rows = table.find_all("tr", recursive=True)
    skill = {"slot": None, "name": None, "description": None, "multipliers": {}}

    if not rows:
        return skill

    # Row 0: "{slot} {name}" where slot is one of the known skill-slot labels.
    header_text = rows[0].get_text(" ", strip=True)
    matched_slot = None
    for label in _SKILL_SLOT_LABELS:
        if header_text.startswith(label):
            matched_slot = label
            break
    if matched_slot:
        skill["slot"] = matched_slot
        skill["name"] = header_text[len(matched_slot):].strip()
    else:
        parts = header_text.split(" ", 1)
        if len(parts) == 2:
            skill["slot"], skill["name"] = parts[0], parts[1]
        elif parts:
            skill["name"] = parts[0]

    # Row 1: "스킬 소개 {description}"
    if len(rows) > 1:
        desc = rows[1].get_text(" ", strip=True)
        desc = re.sub(r"^스킬\s*소개\s*", "", desc)
        skill["description"] = desc.strip() or None

    # Multiplier rows: find a row containing "SKILL LEVEL" and read the
    # detail sub-rows that follow (each "label | v1 v2 ... v10").
    for r in rows[2:]:
        cells = r.find_all(["td", "th"])
        if len(cells) != 2:
            continue
        label = cells[0].get_text(" ", strip=True)
        value = cells[1].get_text(" ", strip=True)
        if not label or not value:
            continue
        if label in ("SKILL LEVEL",):
            continue
        if any(hint in label for hint in _SKILL_LEVEL_ROW_HINTS):
            max_val = _extract_max_level_value(value)
            if max_val:
                skill["multipliers"][label] = max_val

    return skill


def _parse_skills(blocks: list[Tag]) -> list[dict]:
    skills = []
    for title, sub_blocks in _subsections(blocks, "스킬") or []:
        # title looks like "기본 공격: 펠로, 천천히" -- keep as slot label context
        table = _first_table(sub_blocks)
        if table is None:
            continue
        parsed = _parse_skill_table(table)
        if parsed.get("name") is None:
            parsed["name"] = title
        skills.append(parsed)
    return skills


# ---------------------------------------------------------------------------
# Resonance chain (3.3)
# ---------------------------------------------------------------------------

def _parse_resonance_chain(blocks: list[Tag]) -> list[dict]:
    section = _section_blocks(blocks, "공명 체인")
    chain = []
    tables = _all_tables(section)
    for i, t in enumerate(tables[:6], start=1):
        rows = t.find_all("tr")
        if not rows:
            continue
        header = rows[0].get_text(" ", strip=True)
        m = re.search(r"CHAIN\.(\d+)", header)
        seq = int(m.group(1)) if m else i
        name = re.sub(r"\s*CHAIN\.\d+\s*$", "", header).strip()
        effect = rows[1].get_text(" ", strip=True) if len(rows) > 1 else None
        chain.append({"seq": seq, "name": name or None, "effect": effect})
    return chain


# ---------------------------------------------------------------------------
# 운영 (6): teams, weapons, echoes
# ---------------------------------------------------------------------------

def _char_links(tag: Tag) -> list[str]:
    names = []
    for a in tag.find_all("a", attrs={"title": True}):
        title = a["title"]
        m = _CHAR_LINK_RE.match(title)
        if m:
            names.append(m.group(1))
    return names


def _parse_teams(blocks: list[Tag]) -> list[dict]:
    teams = []
    combo_section = _section_blocks(blocks, "조합")
    for title, sub_blocks in _subsections(blocks, "조합") or []:
        tables = _all_tables(sub_blocks)
        if tables:
            # Card-style layout: one table per suggested team, team name is
            # the leading text, teammates are character links within it.
            for t in tables:
                teammates = _char_links(t)
                full_text = t.get_text(" ", strip=True)
                team_name = full_text.split(" ", 1)[0] if full_text else title
                teams.append({
                    "label": title,
                    "team_name": team_name,
                    "teammates": teammates,
                    "note": full_text,
                })
        else:
            # Prose-style layout (subsection titled by role, e.g. "메인 딜러"):
            # collect all linked characters mentioned in the discussion.
            teammates: list[str] = []
            note_parts = []
            for b in sub_blocks:
                teammates.extend(_char_links(b))
                txt = b.get_text(" ", strip=True)
                if txt:
                    note_parts.append(txt)
            if teammates or note_parts:
                # de-duplicate while preserving order
                seen_names = set()
                uniq = []
                for n in teammates:
                    if n not in seen_names:
                        seen_names.add(n)
                        uniq.append(n)
                teams.append({
                    "label": title,
                    "team_name": title,
                    "teammates": uniq,
                    "note": " ".join(note_parts)[:2000],
                })
    return teams


_WEAPON_TYPE_NAV_RE = re.compile(
    r"^(?:대검\s*직검\s*권총\s*권갑\s*증폭기|직검\s*대검\s*권총\s*권갑\s*증폭기)\s*"
)


def _weapon_name(txt: str) -> Optional[str]:
    # Full weapon-card text is "{name}{weapon-type nav strip}Lv. 90 기준 ..."
    # where the nav strip is the 5 weapon-type category words (space
    # separated, order may vary by game). Strip it off if present right after
    # the name.
    m = re.match(
        r"^(.*?)\s*(?:대검|직검|권총|권갑|증폭기)\s*(?:대검|직검|권총|권갑|증폭기)\s*"
        r"(?:대검|직검|권총|권갑|증폭기)\s*(?:대검|직검|권총|권갑|증폭기)\s*"
        r"(?:대검|직검|권총|권갑|증폭기)\s*Lv\.",
        txt,
    )
    if m and m.group(1).strip():
        return m.group(1).strip()
    # Compact variant has no nav strip: name is the text before a stat label.
    m = re.match(r"^(.*?)\s*(?:공격력|크리티컬|공명 효율)\s*\d", txt)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return txt.split(" ", 1)[0] if txt else None


def _parse_weapons(blocks: list[Tag]) -> dict:
    result = {"5star": [], "4star": []}
    for title, sub_blocks in _subsections(blocks, "무기") or []:
        tables = _all_tables(sub_blocks)
        bucket = "5star" if "5성" in title else ("4star" if "4성" in title else None)
        if bucket is None:
            continue
        seen: dict[str, dict] = {}
        order: list[str] = []
        for t in tables:
            txt = t.get_text(" ", strip=True)
            name = _weapon_name(txt)
            if not name:
                continue
            if name not in seen:
                order.append(name)
                seen[name] = {"name": name, "raw": txt}
            elif len(txt) > len(seen[name]["raw"]):
                seen[name]["raw"] = txt
        result[bucket] = [seen[n] for n in order]
    return result


def _parse_echoes(blocks: list[Tag]) -> dict:
    echoes: dict = {
        "main_echo": None,
        "main_echo_description": None,
        "sonata_effects": None,
        "stat_priorities": None,
    }
    for title, sub_blocks in _subsections(blocks, "에코") or []:
        tables = _all_tables(sub_blocks)
        if not tables:
            continue
        txt = tables[0].get_text(" ", strip=True)
        if "에코 어빌리티" in title:
            parts = txt.split("에코 어빌리티", 1)
            if parts:
                head = parts[0].strip()
                # main echo name is first token before "COST"
                m = re.match(r"^(.*?)(?:\s*COST)", head)
                echoes["main_echo"] = m.group(1).strip() if m else head or None
            if len(parts) > 1:
                echoes["main_echo_description"] = parts[1].strip() or None
        elif "화음 이펙트" in title:
            echoes["sonata_effects"] = txt or None
        elif "에코 옵티마이즈" in title:
            echoes["stat_priorities"] = txt or None
    return echoes


# ---------------------------------------------------------------------------
# 평가 (7): pros / cons
# ---------------------------------------------------------------------------

def _parse_list_items(blocks: list[Tag]) -> list[str]:
    items = []
    for b in blocks:
        for li in b.find_all("li"):
            txt = li.get_text(" ", strip=True)
            if txt:
                items.append(txt)
    return items


def _parse_pros_cons(blocks: list[Tag]) -> tuple[list[str], list[str]]:
    pros, cons = [], []
    for title, sub_blocks in _subsections(blocks, "평가") or []:
        if "장점" in title:
            pros = _parse_list_items(sub_blocks)
        elif "단점" in title:
            cons = _parse_list_items(sub_blocks)
    return pros, cons


# ---------------------------------------------------------------------------
# Stats / ascension (3.1)
# ---------------------------------------------------------------------------

def _parse_stats(blocks: list[Tag]) -> Optional[dict]:
    section = _section_blocks(blocks, "속성")
    table = _first_table(section)
    if table is None:
        return None
    txt = table.get_text(" ", strip=True)
    stats: dict = {}
    m = re.search(r"Lv\.\s*([\d/]+)", txt)
    if m:
        stats["level"] = m.group(1)
    for key, label in (
        ("HP", "hp"), ("공격력", "atk"), ("방어력", "def"),
        ("공명 효율", "energy_regen"), ("크리티컬 피해", "crit_dmg"),
        ("크리티컬", "crit_rate"),
    ):
        pattern = re.escape(key) + r"\s*([\d.]+%?)"
        mm = re.search(pattern, txt)
        if mm:
            stats[label] = mm.group(1)
    return stats or None


def _parse_ascension(blocks: list[Tag]) -> list[dict]:
    section = _section_blocks(blocks, "공명자 돌파")
    table = _first_table(section)
    ranks = []
    if table is None:
        return ranks
    txt = table.get_text("\n", strip=True)
    for m in re.finditer(
        r"Rank\.(\d)\s*돌파.*?기초\s*HP\s*(\d+)\s*>>\s*(\d+).*?기초\s*공격력\s*(\d+)\s*>>\s*(\d+).*?기초\s*방어력\s*(\d+)\s*>>\s*(\d+)",
        txt, re.S,
    ):
        ranks.append({
            "rank": int(m.group(1)),
            "hp": {"before": int(m.group(2)), "after": int(m.group(3))},
            "atk": {"before": int(m.group(4)), "after": int(m.group(5))},
            "def": {"before": int(m.group(6)), "after": int(m.group(7))},
        })
    return ranks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_character(html: str) -> dict:
    """Parse a Namuwiki WuWa character page into a normalized dict.

    Defensive: any missing section results in an empty/None field rather than
    an exception.
    """
    soup = BeautifulSoup(html, "lxml")
    blocks = _blocks(soup)

    result: dict = {}
    gaps: list[str] = []

    try:
        result.update(_parse_basic_info(soup, blocks))
    except Exception:
        gaps.append("basic_info")

    try:
        result["skills"] = _parse_skills(blocks)
    except Exception:
        result["skills"] = []
        gaps.append("skills")

    try:
        result["resonance_chain"] = _parse_resonance_chain(blocks)
    except Exception:
        result["resonance_chain"] = []
        gaps.append("resonance_chain")

    try:
        weapons = _parse_weapons(blocks)
        result["recommended_weapons"] = weapons
    except Exception:
        result["recommended_weapons"] = {"5star": [], "4star": []}
        gaps.append("recommended_weapons")

    try:
        result["recommended_echoes"] = _parse_echoes(blocks)
    except Exception:
        result["recommended_echoes"] = {}
        gaps.append("recommended_echoes")

    try:
        result["recommended_teams"] = _parse_teams(blocks)
    except Exception:
        result["recommended_teams"] = []
        gaps.append("recommended_teams")

    try:
        pros, cons = _parse_pros_cons(blocks)
        result["pros"] = pros
        result["cons"] = cons
    except Exception:
        result["pros"] = []
        result["cons"] = []
        gaps.append("pros_cons")

    try:
        result["stats"] = _parse_stats(blocks)
    except Exception:
        result["stats"] = None
        gaps.append("stats")

    try:
        result["ascension"] = _parse_ascension(blocks)
    except Exception:
        result["ascension"] = []
        gaps.append("ascension")

    if gaps:
        result["_gaps"] = gaps

    return result


if __name__ == "__main__":
    import json
    import sys

    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")
    from src.namu.client import fetch_page

    title = sys.argv[1] if len(sys.argv) > 1 else "로코코(명조: 워더링 웨이브)"
    html = fetch_page(title)
    data = parse_character(html)
    print(json.dumps(data, ensure_ascii=False, indent=2)[:6000])
