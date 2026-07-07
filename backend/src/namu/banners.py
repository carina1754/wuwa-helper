"""Parser for Namuwiki Wuthering Waves (명조: 워더링 웨이브) banner/pickup history pages.

Target pages:
  - 명조: 워더링 웨이브/튜닝/캐릭터 이벤트 튜닝   (kind='character')
  - 명조: 워더링 웨이브/튜닝/무기 이벤트 튜닝     (kind='weapon')

Structure discovered on these pages (as of 2026-07):
  - h3/h4 headings carry the game-version grouping, e.g. "3.3.5. 3.4 버전 [편집]"
    (only the "X.X 버전" heading, at h4 depth under the "3.X 버전"/"3.3." h3, actually
    has per-banner detail; "1.X 버전"/"2.X 버전" h3 sections just point to separate
    sub-articles and contain no banner tables on this page).
  - h5 headings under each version, e.g. "3.3.6.1. 깃털에 실은 만물의 소리 [편집]",
    each start one banner ("phase"). The banner's number-within-version (1, 2, 3, ...)
    is used as `phase`, and the heading text (stripped of the "[편집]" edit link and
    the numbering prefix) is used as the banner name.
  - Immediately after the heading there is an image/table block showing the featured
    5-star (and 4-star) items with their icon <img alt="명조 {name} 아이콘"> tags.
  - A line of plain text "이벤트 기간 동안 5성 캐릭터/무기 「A」(, 4성 캐릭터 「B」, 「C」, ...)
    의 튜닝 확률 한정 UP!" names the actually-featured items for that banner. The 5-star
    name(s) right after "5성 캐릭터"/"5성 무기" are used as `items` (there can be more
    than one for "여정이 남긴 ..." rerun-selector banners).
  - A "✦이벤트 기간✦" marker is followed by a line with the date range, one of:
      "X.X 버전 업데이트 이후 ~ 2026년 7월 31일 10:59"   (phase 1: relative start)
      "2026년 7월 31일 11:00 ~ 2026년 8월 19일 12:59"     (phase 2+: explicit start)
    Dates are always "YYYY년 M월 D일 HH:MM" (KST, no explicit timezone marker on page).

This parser is defensive: any missing piece (dates, items, icons) is simply omitted /
left as None / left as an empty list rather than raising, since Namuwiki formatting is
not perfectly uniform across three years of history.
"""
from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

# "3.3.6.1. 깃털에 실은 만물의 소리 [편집]" / "2.3.6.1. 「아득히 푸른 하늘」 [편집]"
_HEADING_NUM_RE = re.compile(r"^(?P<num>[\d.]+)\.\s*(?P<name>.*)$")

# "3.3.6. 3.5 버전 [편집]" -> version "3.5"
_VERSION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*버전")

# Explicit date: "2026년 7월 31일 11:00" (time is optional)
_DATE_RE = re.compile(
    r"(?P<y>\d{4})년\s*(?P<m>\d{1,2})월\s*(?P<d>\d{1,2})일"
    r"(?:\s*(?P<hh>\d{1,2}):(?P<mm>\d{2}))?"
)

# The stray "(☆)" marker on rerun banner titles.
_REDO_MARKER_RE = re.compile(r"\s*\(☆\)\s*")

# Ad / footer boundary markers we must not read past when walking a section's content.
_STOP_TEXT_MARKERS = (
    "이 저작물은",
    "CC BY-NC-SA",
    "나무위키는 백과사전이 아니며",
    "나무위키는 위키위키입니다",
)


def _clean_heading_text(raw: str) -> tuple[Optional[str], str]:
    """Split a heading's text into (numbering, name), stripping the '[편집]' suffix."""
    text = raw.replace("[편집]", "").strip()
    m = _HEADING_NUM_RE.match(text)
    if m:
        return m.group("num"), m.group("name").strip()
    return None, text


def _normalize_date(y: str, m: str, d: str, hh: Optional[str], mm: Optional[str]) -> str:
    if hh is not None and mm is not None:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d} {int(hh):02d}:{mm}"
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def _parse_date_range(period_text: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a '이벤트 기간' value into (start_date, end_date).

    Handles both:
      "3.5 버전 업데이트 이후 ~ 2026년 7월 31일 10:59"  -> start=None (relative), end=date
      "2026년 7월 31일 11:00 ~ 2026년 8월 19일 12:59"    -> start=date, end=date
    """
    if not period_text:
        return None, None
    parts = period_text.split("~")
    start_raw = parts[0].strip() if len(parts) > 0 else ""
    end_raw = parts[1].strip() if len(parts) > 1 else ""

    start_date = None
    m = _DATE_RE.search(start_raw)
    if m:
        start_date = _normalize_date(m.group("y"), m.group("m"), m.group("d"), m.group("hh"), m.group("mm"))
    else:
        # relative start like "3.5 버전 업데이트 이후" -- keep the raw phrase so callers
        # can still tell *something* was there, even though it isn't an absolute date.
        start_date = start_raw or None

    end_date = None
    m = _DATE_RE.search(end_raw)
    if m:
        end_date = _normalize_date(m.group("y"), m.group("m"), m.group("d"), m.group("hh"), m.group("mm"))

    return start_date, end_date


def _iter_section_nodes(start_heading: Tag, stop_heading_names: set[str]):
    """Yield all descendant nodes after `start_heading` until the next heading of
    equal-or-higher level (any tag name in stop_heading_names), or an ad/footer
    boundary. Uses .next_elements which walks the whole subsequent document in
    document order (headings on Namuwiki pages are not simple siblings of their
    section content -- the DOM nesting is inconsistent -- so this is the robust way).
    """
    for el in start_heading.next_elements:
        name = getattr(el, "name", None)
        if name in stop_heading_names:
            return
        if isinstance(el, Tag):
            cls = el.get("class") or []
            if isinstance(cls, str):
                cls = [cls]
            # Ad containers / footer wrapper seen on these pages.
            if any(c in ("WhhI77WT",) for c in cls):
                return
        if isinstance(el, str):
            stripped = el.strip()
            if stripped and any(marker in stripped for marker in _STOP_TEXT_MARKERS):
                return
        yield el


def _section_text_tokens(start_heading: Tag, stop_heading_names: set[str]) -> list[str]:
    tokens: list[str] = []
    for el in _iter_section_nodes(start_heading, stop_heading_names):
        if isinstance(el, str):
            t = el.strip()
            if t:
                tokens.append(t)
    return tokens


def _section_icons(start_heading: Tag, stop_heading_names: set[str]) -> list[dict]:
    icons: list[dict] = []
    seen_src = set()
    for el in _iter_section_nodes(start_heading, stop_heading_names):
        if isinstance(el, Tag) and el.name == "img":
            src = el.get("data-src") or el.get("src") or ""
            if not src or src.startswith("data:"):
                continue
            if src.startswith("//"):
                src = "https:" + src
            if src in seen_src:
                continue
            seen_src.add(src)
            alt = (el.get("alt") or "").strip()
            icons.append({"alt": alt, "src": src})
    return icons


def _extract_featured_items(tokens: list[str], star_label: str) -> list[str]:
    """From the section's flattened text tokens, find the
    '이벤트 기간 동안 5성 {캐릭터|무기}' 「A」 [NEW] [, 4성 ... 「B」, 「C」...] '의 튜닝 확률 한정 UP!'
    sentence and return the 5-star featured item name(s) (there is normally one,
    but rerun/"여정이 남긴" selector banners list several).

    Namuwiki renders this whole lead-in ("이벤트 기간 동안 5성 캐릭터") as a single text
    node/token (not split on whitespace), so we match by substring/suffix rather than
    exact token equality.
    """
    items: list[str] = []

    anchor_idx = None
    for i, t in enumerate(tokens):
        if "이벤트 기간 동안" in t and t.rstrip().endswith(star_label):
            anchor_idx = i
            break
    if anchor_idx is None:
        return items

    # Walk forward collecting 「...」-quoted names until we hit a token that starts
    # the 4-star clause (starts with "," or contains "4성") or the "UP!" end marker.
    for j in range(anchor_idx + 1, min(anchor_idx + 12, len(tokens))):
        t = tokens[j]
        if "4성" in t or "UP!" in t or "의 튜닝" in t:
            break
        m = re.match(r"^「(.+)」$", t)
        if m:
            items.append(m.group(1))
        elif t in (",", "NEW"):
            continue
        else:
            if items:
                break
    return items


def _extract_period(tokens: list[str]) -> Optional[str]:
    for i, t in enumerate(tokens):
        if "이벤트 기간" in t and "✦" in t:
            if i + 1 < len(tokens):
                return tokens[i + 1]
    return None


def _banner_name_from_heading(name: str) -> str:
    """Strip the "(☆)" rerun marker and any 「」 quotes around a weapon banner name."""
    name = _REDO_MARKER_RE.sub("", name).strip()
    m = re.match(r"^「(.+)」$", name)
    if m:
        name = m.group(1)
    return name


def parse_banner_history(html: str, kind: str) -> list:
    """Parse a Namuwiki banner-history page into a list of banner dicts.

    Args:
        html: full page HTML (as returned by src.namu.client.fetch_page).
        kind: 'character' or 'weapon' -- selects the "5성 캐릭터"/"5성 무기" label
              used to locate the featured-item sentence within each banner section.

    Returns:
        list of dicts, each:
          {
            "version": "3.4",              # game version string, or None if unknown
            "phase": 1,                     # 1-based banner index within the version
                                             # (int) when derivable from the heading
                                             # numbering, else None
            "banner_name": "내일에 인화될 기억",
            "is_rerun": False,               # True if heading carried a "(☆)" marker
            "items": ["단근"],               # featured 5-star name(s)
            "start_date": "2026-05-21",       # "YYYY-MM-DD[ HH:MM]" or a relative
                                              # phrase like "3.4 버전 업데이트 이후"
                                              # when no absolute start date is given,
                                              # or None if not found at all
            "end_date": "2026-06-07 12:59",   # "YYYY-MM-DD HH:MM" or None
            "icons": [{"alt": ..., "src": "https://i.namu.wiki/..."}, ...],
          }

        Ordered by document order (i.e. roughly chronological, oldest version first).
        Never raises on a malformed/missing section -- such sections are simply
        omitted or emitted with fewer populated fields.
    """
    star_label = "5성 캐릭터" if kind == "character" else "5성 무기"

    soup = BeautifulSoup(html, "lxml")

    all_headings = soup.find_all(["h2", "h3", "h4", "h5"])
    heading_names = {"h2", "h3", "h4", "h5"}

    results: list[dict] = []

    current_version: Optional[str] = None
    version_level: Optional[int] = None
    phase_counter = 0

    for h in all_headings:
        raw_text = h.get_text(" ", strip=True)
        level = int(h.name[1])  # "h4" -> 4

        # A "X.X 버전" heading opens a version group. Its heading depth varies by
        # page: the master 튜닝 page nests versions at h4 (banners at h5), while the
        # per-era sub-articles (.../튜닝/캐릭터 이벤트 튜닝/1.X 버전, /2.X 버전) nest
        # versions at h2 (banners at h3). We detect the version depth dynamically and
        # treat any deeper heading as a banner within it. Roll-up headings like
        # "1.X 버전"/"3.X 버전" carry no absolute version number (X is not a digit) and
        # never match, so they never open a group.
        m = _VERSION_RE.search(raw_text)
        if m:
            current_version = m.group(1)
            version_level = level
            phase_counter = 0
            continue

        # A non-version heading at or above the version's depth (e.g. "개요",
        # "관련 틀") closes the current group; only strictly-deeper headings are its
        # banners.
        if version_level is not None and level <= version_level:
            current_version = None
            version_level = None
            continue

        if current_version is None:
            # Banner heading outside any recognised "X.X 버전" group -- skip defensively.
            continue

        phase_counter += 1
        _, name = _clean_heading_text(raw_text)
        is_rerun = "☆" in name
        banner_name = _banner_name_from_heading(name)

        tokens = _section_text_tokens(h, heading_names)
        items = _extract_featured_items(tokens, star_label)
        period_text = _extract_period(tokens)
        start_date, end_date = _parse_date_range(period_text) if period_text else (None, None)
        icons = _section_icons(h, heading_names)

        results.append(
            {
                "version": current_version,
                "phase": phase_counter,
                "banner_name": banner_name,
                "is_rerun": is_rerun,
                "items": items,
                "start_date": start_date,
                "end_date": end_date,
                "icons": icons,
            }
        )

    return results


if __name__ == "__main__":
    import json
    import sys

    sys.path.insert(0, r"C:/Users/JungSu/Desktop/wawa-ai-coach/backend")
    from src.namu.client import fetch_page, sub_page  # noqa: E402

    char_html = fetch_page(sub_page("튜닝", "캐릭터 이벤트 튜닝"))
    weapon_html = fetch_page(sub_page("튜닝", "무기 이벤트 튜닝"))

    char_banners = parse_banner_history(char_html, "character")
    weapon_banners = parse_banner_history(weapon_html, "weapon")

    print(f"character banners: {len(char_banners)}")
    print(f"weapon banners: {len(weapon_banners)}")

    print("\n--- sample character banners (last 6) ---")
    for b in char_banners[-6:]:
        b2 = dict(b)
        b2["icons"] = f"<{len(b['icons'])} icons>"
        print(json.dumps(b2, ensure_ascii=False))

    print("\n--- sample weapon banners (last 6) ---")
    for b in weapon_banners[-6:]:
        b2 = dict(b)
        b2["icons"] = f"<{len(b['icons'])} icons>"
        print(json.dumps(b2, ensure_ascii=False))
