# -*- coding: utf-8 -*-
"""
Namuwiki parser for Wuthering Waves (명조: 워더링 웨이브) ECHO system.

Two independent extraction targets, both defensive (missing section -> empty list,
never crash on unexpected structure):

1. parse_sonata_sets(html) -> list[dict]
   Source page: 명조: 워더링 웨이브/데이터 스테이션  (section "4. 화음 도감")
   Each sonata set is an <h4> heading ("4.x.y.<이름>[편집]") followed by a table
   with rows:
     row0: set name + icon (header bar)
     row1: <ul><li> two_piece effect, <li> five_piece effect
     row2 (optional): a collapsible <details> block listing which enemy-tier
                      echoes belong to this sonata (grouped by tier/cost)

2. parse_echoes(html) -> list[dict]
   Source pages: 명조: 워더링 웨이브/적/{해일급,노도급,거랑급,경파급,특수 몬스터}
   Each individual echo (monster) is an <h3> (or <h4> for "악몽 · X" nightmare
   variants) heading followed by a table whose first row has the icon + KO name
   + tier text (해일급/노도급/거랑급/경파급).

Because sonata membership is not listed on the per-echo page itself, parse_echoes()
also accepts an optional `sonata_sets` argument (the output of parse_sonata_sets on
the 데이터 스테이션 page) to fill in `sonata_memberships` for each echo by name
cross-reference. Without it, sonata_memberships is left as an empty list.

Namuwiki HTML is deeply nested and noisy (base64 placeholder <img> + a real
<img class="... Mcf1giQg" data-src="...">). All cell/heading lookups below are
defensive: a missing/renamed section is skipped rather than raising.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

_EDIT_SUFFIX_RE = re.compile(r"\[편집\]\s*$")
_NUM_PREFIX_RE = re.compile(r"^\s*[\d.]+\s*")

# Tier (위험 등급) -> normalized klass / cost, per the "코스트에 따른 분류" table:
#   해일급 (Calamity) : COST 4, unique-per-field
#   노도급 (Overlord)  : COST 4
#   거랑급 (Elite)     : COST 3
#   경파급 (Common)    : COST 1
_TIER_INFO = {
    "해일급": {"klass": "calamity", "cost": 4},
    "노도급": {"klass": "overlord", "cost": 4},
    "거랑급": {"klass": "elite", "cost": 3},
    "경파급": {"klass": "common", "cost": 1},
}


def _get_content_root(soup: BeautifulSoup) -> Optional[Tag]:
    """The article body is the div with the most direct element children
    (Namuwiki wraps every block -- heading/table/paragraph -- in its own
    wrapper div, all as direct children of one big content container)."""
    best = None
    best_n = -1
    for div in soup.find_all("div"):
        n = sum(1 for c in div.children if isinstance(c, Tag))
        if n > best_n:
            best_n = n
            best = div
    return best


def _heading_text(tag: Tag) -> str:
    """Clean a heading's text: drop numeric prefix and trailing [편집]."""
    txt = tag.get_text(" ", strip=True)
    txt = _EDIT_SUFFIX_RE.sub("", txt)
    txt = _NUM_PREFIX_RE.sub("", txt)
    return txt.strip()


def _real_img_src(tag: Tag) -> Optional[str]:
    """Namuwiki renders a base64 SVG placeholder plus a real <img> carrying
    data-src (lazy-load). Find the real one and normalize to an https URL."""
    if tag is None:
        return None
    img = tag.find("img", attrs={"data-src": True})
    if img is None:
        img = tag.find("img", src=True)
        if img is None:
            return None
        src = img.get("src")
    else:
        src = img.get("data-src")
    if not src:
        return None
    if src.startswith("//"):
        src = "https:" + src
    return src


def _next_table_after(root_children: list, start_idx: int):
    """Given the flat list of direct element children of the content root,
    return the first <table> found in the next 1-3 sibling blocks (stopping
    if another heading is hit first)."""
    for j in range(start_idx + 1, min(start_idx + 4, len(root_children))):
        node = root_children[j]
        if node.find(["h2", "h3", "h4"]):
            break
        t = node.find("table")
        if t is not None:
            return t
    return None


# ---------------------------------------------------------------------------
# 1. Sonata sets  (화음 도감 on 데이터 스테이션 page)
# ---------------------------------------------------------------------------

def parse_sonata_sets(html: str) -> list:
    """Parse sonata (화음/소나타) set effects from the
    '명조: 워더링 웨이브/데이터 스테이션' page HTML.

    Returns a list of dicts:
      {
        "name_ko": str,
        "two_piece": str | None,
        "five_piece": str | None,
        "icon": str | None,
        "echo_memberships": {tier_ko: [echo_name_ko, ...], ...}   # extra, best-effort
      }
    """
    soup = BeautifulSoup(html, "lxml")
    root = _get_content_root(soup)
    if root is None:
        return []

    children = [c for c in root.children if isinstance(c, Tag)]

    # locate "화음 도감" top-level (h2) section boundaries
    sonata_h2_idx = None
    next_h2_idx = None
    for i, c in enumerate(children):
        h = c.find("h2") if c.name != "h2" else c
        if h is None:
            continue
        txt = _heading_text(h)
        if sonata_h2_idx is None and "화음 도감" in txt:
            sonata_h2_idx = i
            continue
        if sonata_h2_idx is not None and i > sonata_h2_idx:
            next_h2_idx = i
            break
    if sonata_h2_idx is None:
        return []
    end = next_h2_idx if next_h2_idx is not None else len(children)

    results = []
    for i in range(sonata_h2_idx + 1, end):
        node = children[i]
        h = node.find("h4") if node.name != "h4" else node
        if h is None:
            continue
        name = _heading_text(h)
        if not name:
            continue

        table = _next_table_after(children, i)
        entry = {
            "name_ko": name,
            "two_piece": None,
            "five_piece": None,
            "icon": None,
            "echo_memberships": {},
        }
        if table is None:
            results.append(entry)
            continue

        rows = table.find_all("tr")
        # row 0: header bar with set name + icon
        if rows:
            entry["icon"] = _real_img_src(rows[0])

        # row 1 (occasionally row 2): <ul><li> per-piece-count effect text.
        # Most sonata sets use (2/2) + (5/5); some boss-only/legendary sonatas
        # only have a single (3/3) tier instead. Capture whatever piece counts
        # are actually present rather than assuming 2/5.
        pieces: dict = {}
        for row in rows[1:3]:
            lis = row.find_all("li")
            if not lis:
                continue
            for li in lis:
                txt = li.get_text(" ", strip=True)
                m = re.search(r"\((\d+)/(\d+)\)", txt)
                if not m:
                    continue
                n_active = int(m.group(1))
                # strip "<name> (n/n)" prefix, keep the effect description
                after = txt.split(")", 1)
                desc = after[1].strip() if len(after) > 1 else txt
                pieces[n_active] = desc
            if pieces:
                break
        entry["two_piece"] = pieces.get(2)
        entry["five_piece"] = pieces.get(5)
        if pieces and not (entry["two_piece"] or entry["five_piece"]):
            # e.g. a lone (3/3) boss-sonata effect -- surface it too so it
            # isn't silently dropped, keyed by its actual piece count.
            entry["other_pieces"] = pieces

        # remaining rows: <details> block listing echo membership by tier
        memberships: dict = {}
        details = table.find("details")
        if details is not None:
            inner = details.find("table")
            if inner is not None:
                current_tier = None
                for row in inner.find_all("tr"):
                    cell = row.find(["td", "th"])
                    if cell is None:
                        continue
                    links = cell.find_all("a")
                    if not links:
                        tier_txt = cell.get_text(" ", strip=True)
                        if tier_txt:
                            current_tier = tier_txt
                            memberships.setdefault(current_tier, [])
                        continue
                    if current_tier is None:
                        current_tier = "?"
                        memberships.setdefault(current_tier, [])
                    for a in links:
                        href = a.get("href", "")
                        frag = href.split("#", 1)[1] if "#" in href else ""
                        frag = urllib.parse.unquote(frag).strip()
                        if frag:
                            memberships[current_tier].append(frag)
        entry["echo_memberships"] = memberships

        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# 2. Individual echoes (적/해일급, 적/노도급, 적/거랑급, 적/경파급, 적/특수 몬스터)
# ---------------------------------------------------------------------------

def parse_echoes(html: str, sonata_sets: Optional[list] = None) -> list:
    """Parse individual echo (enemy) entries from one of the
    '명조: 워더링 웨이브/적/{tier}' pages.

    `sonata_sets`: optionally pass the list returned by parse_sonata_sets()
    (parsed from the 데이터 스테이션 page) to fill in `sonata_memberships`
    for each echo via name cross-reference. If omitted, sonata_memberships
    is always [].

    Returns a list of dicts:
      {
        "name_ko": str,
        "cost": 1 | 3 | 4 | None,
        "klass": "calamity" | "overlord" | "elite" | "common" | None,
        "sonata_memberships": [sonata_name_ko, ...],
        "icon": str | None,
      }
    """
    soup = BeautifulSoup(html, "lxml")
    root = _get_content_root(soup)
    if root is None:
        return []

    children = [c for c in root.children if isinstance(c, Tag)]

    # Build name -> [sonata names] map if sonata_sets provided
    name_to_sonatas: dict = {}
    if sonata_sets:
        for s in sonata_sets:
            sname = s.get("name_ko")
            if not sname:
                continue
            for tier_echoes in (s.get("echo_memberships") or {}).values():
                for echo_name in tier_echoes:
                    name_to_sonatas.setdefault(echo_name, []).append(sname)

    results = []
    for i, node in enumerate(children):
        h = None
        if node.name in ("h3", "h4"):
            h = node
        else:
            # Namuwiki sometimes wraps a heading in several layers of empty
            # placeholder divs (e.g. class "WwZNj9Bc") before the actual
            # h3/h4 -- search recursively rather than only direct children.
            h = node.find(["h3", "h4"])
        if h is None:
            continue

        # Skip the top-of-page TOC-ish / overview headings ("1.개요", "2.목록", "2.1 잔상" etc.
        # are handled naturally since they simply won't have an echo-shaped table following them)
        name = _heading_text(h)
        if not name:
            continue

        table = _next_table_after(children, i)
        if table is None:
            continue

        rows = table.find_all("tr")
        if not rows:
            continue
        header_row = rows[0]
        header_text = header_row.get_text(" ", strip=True)

        # Determine tier from header row text (해일급/노도급/거랑급/경파급)
        tier = None
        for t in _TIER_INFO:
            if t in header_text:
                tier = t
                break
        if tier is None:
            # Not an echo entry table (e.g. lore/overview tables) -> skip
            continue

        icon = _real_img_src(header_row)
        info = _TIER_INFO[tier]

        results.append({
            "name_ko": name,
            "cost": info["cost"],
            "klass": info["klass"],
            "sonata_memberships": sorted(set(name_to_sonatas.get(name, []))),
            "icon": icon,
        })

    return results


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    sys.path.insert(0, ".")
    from src.namu.client import fetch_page, sub_page  # noqa: E402

    ds_html = fetch_page(sub_page("데이터 스테이션"))
    sonatas = parse_sonata_sets(ds_html)
    print(f"sonata_sets: {len(sonatas)}")
    print(json.dumps(sonatas[:2], ensure_ascii=False, indent=2))

    all_echoes = []
    for tier_name in ["해일급", "노도급", "거랑급", "경파급", "특수 몬스터"]:
        tier_html = fetch_page(sub_page("적", tier_name))
        echoes = parse_echoes(tier_html, sonata_sets=sonatas)
        print(f"{tier_name}: {len(echoes)} echoes")
        all_echoes.extend(echoes)

    print(f"total echoes: {len(all_echoes)}")
    print(json.dumps(all_echoes[:5], ensure_ascii=False, indent=2))
    with_sonata = [e for e in all_echoes if e["sonata_memberships"]]
    print(f"echoes with sonata membership resolved: {len(with_sonata)}")
    print(json.dumps(with_sonata[:5], ensure_ascii=False, indent=2))
