from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from .database import get_connection

OFFICIAL_JSON_BASE_URL = "https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152"
OFFICIAL_SITE_BASE_URL = "https://wutheringwaves.kurogames.com"
OFFICIAL_NEWS_URL = f"{OFFICIAL_SITE_BASE_URL}/kr/main/news"
PC_GAMER_BANNERS_URL = "https://www.pcgamer.com/games/rpg/wuthering-waves-banner-next-current/"
REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "WuWaHelper/1.0"})
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="ignore")
    parser = TextExtractor()
    parser.feed(html)
    return "\n".join(parser.parts)


def _fetch_json(url: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": "WuWaHelper/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))




def _fetch_official_json(locale: str, filename: str) -> dict[str, object]:
    return _fetch_json(f"{OFFICIAL_JSON_BASE_URL}/{locale}/{filename}")


def _plain_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(unescape(text).split())


def _article_link(locale: str, article_id: int) -> str:
    return f"{OFFICIAL_SITE_BASE_URL}/{locale}/main/news/detail/{article_id}"


def _extract_version_from_article(title: str, content: str) -> str | None:
    text = f"{title} {content}"
    match = re.search(r"(?:Version\s*)?(\d+\.\d+)|(?:(\d+\.\d+)\s*버전)", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1) or match.group(2)


def _format_kst(year: int, month: int, day: int, hour: int, minute: int, add_utc8_offset: bool = False) -> str:
    value = datetime(year, month, day, hour, minute)
    if add_utc8_offset:
        value += timedelta(hours=1)
    return value.strftime("%Y-%m-%d %H:%M KST")


def _extract_release_datetime_kst(text: str) -> str | None:
    utc8_iso_match = re.search(r"(20\d{2})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}).{0,80}?\(UTC\+8\)", text, re.IGNORECASE)
    if utc8_iso_match:
        return _format_kst(*map(int, utc8_iso_match.groups()), add_utc8_offset=True)

    ko_match = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(\d{1,2}):(\d{2})(.{0,30}?\(UTC\+8\))?", text, re.IGNORECASE)
    if ko_match:
        year, month, day, hour, minute = map(int, ko_match.groups()[:5])
        return _format_kst(year, month, day, hour, minute, add_utc8_offset=bool(ko_match.group(6)))

    dotted_match = re.search(r"(20\d{2})\.(\d{1,2})\.(\d{1,2})(?:\([^)]*\))?\s*(\d{1,2}):(\d{2})(.{0,30}?\(UTC\+8\))?", text, re.IGNORECASE)
    if dotted_match:
        year, month, day, hour, minute = map(int, dotted_match.groups()[:5])
        return _format_kst(year, month, day, hour, minute, add_utc8_offset=bool(dotted_match.group(6)))

    iso_match = re.search(r"(20\d{2})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2})", text)
    if iso_match:
        return _format_kst(*map(int, iso_match.groups()))

    date_match = re.search(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if date_match:
        year, month, day = map(int, date_match.groups())
        return f"{year:04d}-{month:02d}-{day:02d} 00:00 KST"
    return None


def _extract_release_date_kst(text: str) -> str | None:
    return _extract_release_datetime_kst(text)


def _is_version_update_article(title: str) -> bool:
    patterns = [
        r"\d+\.\d+\s*버전.*(?:내용 안내|업데이트 점검)",
        r"Version\s+\d+\.\d+\s+Update\s+Maintenance\s+Notice",
        r"Patch Notes for Version\s+\d+\.\d+",
        r"Update Content\s*\|\s*Version\s+\d+\.\d+",
    ]
    return any(re.search(pattern, title, re.IGNORECASE) for pattern in patterns)


def _article_sort_key(article: dict[str, object]) -> datetime:
    value = str(article.get("startTime") or article.get("createTime") or "1970-01-01 00:00:00")
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime(1970, 1, 1)


def _official_candidates(locale: str, since_year: int = 2024) -> list[dict[str, object]]:
    menu = _fetch_official_json(locale, "MainMenu.json")
    articles = list(menu.get("article", [])) if isinstance(menu, dict) else []
    cutoff = datetime(since_year, 1, 1)
    seen_ids: set[int] = set()
    candidates: list[dict[str, object]] = []
    for article in sorted(articles, key=_article_sort_key, reverse=True):
        article_id = int(article.get("articleId") or 0)
        title = str(article.get("articleTitle") or "")
        if not article_id or article_id in seen_ids or _article_sort_key(article) < cutoff or not _is_version_update_article(title):
            continue
        seen_ids.add(article_id)
        candidates.append(article)
    return candidates


def _updates_from_official_articles(since_year: int = 2024, limit: int | None = None) -> list[dict[str, object]]:
    by_version: dict[str, dict[str, object]] = {}
    for locale in ("kr", "en"):
        for article in _official_candidates(locale, since_year=since_year):
            article_id = int(article.get("articleId") or 0)
            detail = _fetch_official_json(locale, f"article/{article_id}.json")
            title = str(detail.get("articleTitle") or article.get("articleTitle") or "")
            content = _plain_text(str(detail.get("articleContent") or ""))
            version = _extract_version_from_article(title, content)
            if not version or version in by_version:
                continue
            release_datetime = _extract_release_datetime_kst(content)
            by_version[version] = {
                "id": f"wuwa-{version.replace('.', '-')}",
                "version": version,
                "title_ko": f"{version} 업데이트",
                "release_date_kst": release_datetime,
                "summary_ko": "",
                "highlights_ko": [],
                "source_links": [_article_link(locale, article_id)],
            }
    updates = sorted(by_version.values(), key=lambda item: item.get("release_date_kst") or "", reverse=True)
    return updates[:limit] if limit is not None else updates


def _parse_month(name: str) -> int:
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    return months[name.lower()]


def _extract_banner_rows(text: str) -> list[dict[str, object]]:
    date_pattern = re.compile(
        r"(?P<start_month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<start_day>\d{1,2}),?\s*(?P<start_year>\d{4})?\s*-\s*"
        r"(?P<end_month>January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(?P<end_day>\d{1,2})(?:,?\s*(?P<end_year>\d{4}))?",
        re.IGNORECASE,
    )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        match = date_pattern.fullmatch(line)
        if not match:
            continue
        banner = lines[index - 2] if index >= 2 else ""
        four_stars = lines[index - 1] if index >= 1 else ""
        if not banner or banner.lower() in {"banner", "four-star characters", "dates"}:
            continue
        start_year = int(match.group("start_year") or match.group("end_year") or datetime.now().year)
        rows.append(
            {
                "banner": banner.strip(),
                "four_stars": [item.strip() for item in four_stars.split(",") if item.strip() and four_stars != "N/A"],
                "start_year": start_year,
                "start_month": _parse_month(match.group("start_month")),
                "start_day": int(match.group("start_day")),
                "end_month": _parse_month(match.group("end_month")),
                "end_day": int(match.group("end_day")),
                "end_year": int(match.group("end_year") or start_year),
            }
        )
    return rows


_CATEGORY_ID_SUFFIXES = {
    "first_pickup": "first",
    "rerun_1": "rerun-1",
    "rerun_2": "rerun-2",
}


def _schedule_from_banner_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    items: list[dict[str, object]] = []
    rows = sorted(rows, key=lambda row: (int(row["start_year"]), int(row["start_month"]), int(row["start_day"]), str(row["banner"])))
    grouped: dict[tuple[int, int, str], list[str]] = {}
    for row in rows:
        banner = str(row["banner"])
        if "(" in banner and "," in banner:
            continue
        category = "rerun_1" if banner in seen else "first_pickup"
        seen.add(banner)
        key = (int(row["start_year"]), int(row["start_month"]), category)
        grouped.setdefault(key, []).append(banner)

    for (year, month, category), characters in sorted(grouped.items()):
        label = "첫 픽업" if category == "first_pickup" else "1차 복각"
        id_suffix = _CATEGORY_ID_SUFFIXES.get(category, category)
        items.append(
            {
                "id": f"{year}-{month:02d}-{id_suffix}",
                "year": year,
                "month": month,
                "category": category,
                "label_ko": label,
                "characters": sorted(set(characters)),
                "notes_ko": "PC Gamer 배너 히스토리에서 자동 갱신됨",
                "source_links": [PC_GAMER_BANNERS_URL],
            }
        )
    return items


def _updates_from_banner_text(text: str) -> list[dict[str, object]]:
    updates: list[dict[str, object]] = []
    version_matches = re.finditer(r"version\s+(?P<version>\d+\.\d+).*?(?P<date>July\s+10|June\s+8|February\s+5)?", text, re.IGNORECASE)
    seen: set[str] = set()
    for match in version_matches:
        version = match.group("version")
        if version in seen:
            continue
        seen.add(version)
        release = None
        if match.group("date") == "July 10":
            release = "2026-07-10"
        elif match.group("date") == "June 8":
            release = "2026-06-08"
        elif match.group("date") == "February 5":
            release = "2026-02-05"
        updates.append(
            {
                "id": f"wuwa-{version}",
                "version": version,
                "title_ko": f"{version} 업데이트",
                "release_date_kst": release,
                "summary_ko": "외부 배너/업데이트 문서에서 자동 확인된 명조 업데이트 항목입니다.",
                "highlights_ko": ["픽업 및 복각 배너 정보 갱신", "한국 기준 표시용 데이터 갱신"],
                "source_links": [PC_GAMER_BANNERS_URL],
            }
        )
    return updates


def _last_refresh(conn, source: str) -> datetime | None:
    row = conn.execute("SELECT refreshed_at FROM refresh_state WHERE source = %s", (source,)).fetchone()
    if not row:
        return None
    try:
        value = datetime.fromisoformat(row["refreshed_at"])
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    except ValueError:
        return None


def should_refresh(source: str) -> bool:
    with get_connection() as conn:
        _ensure_refresh_state(conn)
        last = _last_refresh(conn, source)
    if last is None:
        return True
    return (datetime.now(timezone.utc) - last).total_seconds() >= REFRESH_INTERVAL_SECONDS


def _ensure_refresh_state(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_state (
            source TEXT PRIMARY KEY,
            refreshed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT
        )
        """
    )


def refresh_pickups_and_updates(force: bool = False) -> dict[str, object]:
    source = "kurogames_official_news"
    if not force and not should_refresh(source):
        return {"refreshed": False, "source": source, "reason": "fresh"}
    json_source = os.getenv("CONTENT_REFRESH_JSON_URL")
    if json_source:
        payload = _fetch_json(json_source)
        schedule = list(payload.get("pickup_schedule", []))
        updates = list(payload.get("game_updates", []))
        source_link = json_source
    else:
        schedule = []
        updates = _updates_from_official_articles()
        source_link = OFFICIAL_NEWS_URL
    with get_connection() as conn:
        _ensure_refresh_state(conn)
        if not schedule and not updates:
            conn.execute(
                """
                INSERT INTO refresh_state (source, refreshed_at, status, message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source) DO UPDATE SET
                    refreshed_at = EXCLUDED.refreshed_at,
                    status = EXCLUDED.status,
                    message = EXCLUDED.message
                """,
                (source, _now_iso(), "skipped", f"{source_link} fetched but no official update rows; kept existing DB data"),
            )
            conn.commit()
            return {"refreshed": False, "source": source, "reason": "no_official_rows"}
        for item in schedule:
            conn.execute(
                """
                INSERT INTO pickup_schedule (id, year, month, category, data_json, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    year = EXCLUDED.year,
                    month = EXCLUDED.month,
                    category = EXCLUDED.category,
                    data_json = EXCLUDED.data_json,
                    updated_at = now()
                """,
                (item["id"], item["year"], item["month"], item["category"], json.dumps(item, ensure_ascii=False)),
            )
        for item in updates:
            conn.execute(
                """
                INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    version = EXCLUDED.version,
                    release_date_kst = EXCLUDED.release_date_kst,
                    data_json = EXCLUDED.data_json,
                    updated_at = now()
                """,
                (item["id"], item["version"], item.get("release_date_kst"), json.dumps(item, ensure_ascii=False)),
            )
        conn.execute(
            """
            INSERT INTO refresh_state (source, refreshed_at, status, message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source) DO UPDATE SET
                    refreshed_at = EXCLUDED.refreshed_at,
                    status = EXCLUDED.status,
                    message = EXCLUDED.message
            """,
            (source, _now_iso(), "ok", f"schedule={len(schedule)} updates={len(updates)}"),
        )
        conn.commit()
    return {"refreshed": True, "source": source, "schedule": len(schedule), "updates": len(updates)}


def refresh_pickups_and_updates_if_stale() -> None:
    try:
        refresh_pickups_and_updates(force=False)
    except Exception as exc:
        with get_connection() as conn:
            _ensure_refresh_state(conn)
            conn.execute(
                """
                INSERT INTO refresh_state (source, refreshed_at, status, message)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source) DO UPDATE SET
                    refreshed_at = EXCLUDED.refreshed_at,
                    status = EXCLUDED.status,
                    message = EXCLUDED.message
                """,
                ("kurogames_official_news", _now_iso(), "error", str(exc)),
            )
            conn.commit()


def start_daily_refresh_worker() -> None:
    if os.getenv("DISABLE_CONTENT_REFRESH") == "1":
        return

    def run() -> None:
        refresh_pickups_and_updates_if_stale()
        while True:
            time.sleep(REFRESH_INTERVAL_SECONDS)
            refresh_pickups_and_updates_if_stale()

    thread = threading.Thread(target=run, name="content-refresh", daemon=True)
    thread.start()


