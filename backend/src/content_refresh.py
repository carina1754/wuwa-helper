from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.request import Request, urlopen

from .curated_updates import apply_curated_update_summaries
from .database import get_connection
from .media import ensure_hero_image

OFFICIAL_JSON_BASE_URL = "https://hw-media-cdn-mingchao.kurogame.com/akiwebsite/website2.0/json/G152"
OFFICIAL_SITE_BASE_URL = "https://wutheringwaves.kurogames.com"
OFFICIAL_NEWS_URL = f"{OFFICIAL_SITE_BASE_URL}/kr/main/news"
REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _extract_hero_image_url(raw_content: str) -> str | None:
    match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_content, re.IGNORECASE)
    return match.group(1) if match else None


def _extract_thematic_title(article_title: str, version: str) -> str:
    title = (article_title or "").strip()
    if "내용 안내" in title:
        stripped = re.sub(r"\s*내용\s*안내\s*$", "", title).strip()
        return stripped or f"{version} 업데이트"
    return f"{version} 업데이트"


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
            raw_content = str(detail.get("articleContent") or "")
            content = _plain_text(raw_content)
            version = _extract_version_from_article(title, content)
            if not version or version in by_version:
                continue
            release_datetime = _extract_release_datetime_kst(content)
            by_version[version] = {
                "id": f"wuwa-{version.replace('.', '-')}",
                "version": version,
                "title_ko": _extract_thematic_title(title, version),
                "release_date_kst": release_datetime,
                "summary_ko": "",
                "highlights_ko": [],
                "source_links": [_article_link(locale, article_id)],
                "image_source_url": _extract_hero_image_url(raw_content),
            }
    updates = sorted(by_version.values(), key=lambda item: item.get("release_date_kst") or "", reverse=True)
    return updates[:limit] if limit is not None else updates


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
            source_image_url = item.pop("image_source_url", None)
            existing_row = conn.execute(
                "SELECT data_json FROM game_updates WHERE id = %s", (item["id"],)
            ).fetchone()
            previous = json.loads(existing_row["data_json"]) if existing_row else {}

            # Preserve authored fields the scrape leaves empty.
            if not item.get("summary_ko"):
                item["summary_ko"] = previous.get("summary_ko", "")
            if not item.get("highlights_ko"):
                item["highlights_ko"] = previous.get("highlights_ko", [])

            # Cache the hero image (no-op if already cached); keep a previously
            # cached image when this refresh has no new source.
            image_url = ensure_hero_image(item["id"], source_image_url)
            item["image_url"] = image_url or previous.get("image_url")

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
    apply_curated_update_summaries()
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


