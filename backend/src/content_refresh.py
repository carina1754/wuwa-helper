from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from .database import get_connection

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
        items.append(
            {
                "id": f"{year}-{month:02d}-{category}",
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
    row = conn.execute("SELECT refreshed_at FROM refresh_state WHERE source = ?", (source,)).fetchone()
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
    source = "pcgamer_banners"
    if not force and not should_refresh(source):
        return {"refreshed": False, "source": source, "reason": "fresh"}
    json_source = os.getenv("CONTENT_REFRESH_JSON_URL")
    if json_source:
        payload = _fetch_json(json_source)
        schedule = list(payload.get("pickup_schedule", []))
        updates = list(payload.get("game_updates", []))
        source_link = json_source
    else:
        text = _fetch_text(PC_GAMER_BANNERS_URL)
        schedule = _schedule_from_banner_rows(_extract_banner_rows(text))
        updates = _updates_from_banner_text(text)
        source_link = PC_GAMER_BANNERS_URL
    with get_connection() as conn:
        _ensure_refresh_state(conn)
        if not schedule:
            conn.execute(
                """
                INSERT OR REPLACE INTO refresh_state (source, refreshed_at, status, message)
                VALUES (?, ?, ?, ?)
                """,
                (source, _now_iso(), "skipped", f"{source_link} fetched but no parseable banner rows; kept existing DB data"),
            )
            conn.commit()
            return {"refreshed": False, "source": source, "reason": "no_parseable_rows"}
        for item in schedule:
            conn.execute(
                """
                INSERT OR REPLACE INTO pickup_schedule (id, year, month, category, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (item["id"], item["year"], item["month"], item["category"], json.dumps(item, ensure_ascii=False)),
            )
        for item in updates:
            conn.execute(
                """
                INSERT OR REPLACE INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (item["id"], item["version"], item.get("release_date_kst"), json.dumps(item, ensure_ascii=False)),
            )
        conn.execute(
            """
            INSERT OR REPLACE INTO refresh_state (source, refreshed_at, status, message)
            VALUES (?, ?, ?, ?)
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
                INSERT OR REPLACE INTO refresh_state (source, refreshed_at, status, message)
                VALUES (?, ?, ?, ?)
                """,
                ("pcgamer_banners", _now_iso(), "error", str(exc)),
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
