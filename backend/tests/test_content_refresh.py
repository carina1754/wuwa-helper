from __future__ import annotations

import json

from src import content_refresh
from src.database import get_connection, init_db


def test_refresh_preserves_historical_rows_not_covered_by_new_scrape(monkeypatch):
    init_db()
    cleanup_schedule_ids = ("test-historical-row", "test-current-row")
    cleanup_update_ids = ("test-historical-update", "test-current-update")

    with get_connection() as conn:
        conn.execute("DELETE FROM pickup_schedule WHERE id = ANY(%s)", (list(cleanup_schedule_ids),))
        conn.execute("DELETE FROM game_updates WHERE id = ANY(%s)", (list(cleanup_update_ids),))
        conn.commit()

    with get_connection() as conn:
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
            (
                "test-historical-row",
                2020,
                1,
                "first_pickup",
                json.dumps(
                    {
                        "id": "test-historical-row",
                        "year": 2020,
                        "month": 1,
                        "category": "first_pickup",
                        "label_ko": "첫 픽업",
                        "characters": ["HistoricalCharacter"],
                        "notes_ko": "historical row that must survive a refresh",
                        "source_links": [],
                    },
                    ensure_ascii=False,
                ),
            ),
        )
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
            (
                "test-historical-update",
                "1.0",
                "2020-01-01",
                json.dumps(
                    {
                        "id": "test-historical-update",
                        "version": "1.0",
                        "title_ko": "1.0 업데이트",
                        "release_date_kst": "2020-01-01",
                        "summary_ko": "historical update row that must survive a refresh",
                        "highlights_ko": [],
                        "source_links": [],
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    monkeypatch.setenv("CONTENT_REFRESH_JSON_URL", "https://example.com/feed.json")
    monkeypatch.setattr(
        content_refresh,
        "_fetch_json",
        lambda url: {
            "pickup_schedule": [
                {
                    "id": "test-current-row",
                    "year": 2026,
                    "month": 8,
                    "category": "first_pickup",
                    "label_ko": "첫 픽업",
                    "characters": ["NewCharacter"],
                    "notes_ko": "freshly scraped current row",
                    "source_links": [],
                }
            ],
            "game_updates": [
                {
                    "id": "test-current-update",
                    "version": "2.0",
                    "title_ko": "2.0 업데이트",
                    "release_date_kst": "2026-08-01",
                    "summary_ko": "freshly scraped current update",
                    "highlights_ko": [],
                    "source_links": [],
                }
            ],
        },
    )

    result = content_refresh.refresh_pickups_and_updates(force=True)
    assert result["refreshed"] is True

    with get_connection() as conn:
        ids = {row["id"] for row in conn.execute("SELECT id FROM pickup_schedule").fetchall()}
        update_ids = {row["id"] for row in conn.execute("SELECT id FROM game_updates").fetchall()}

    assert "test-historical-row" in ids
    assert "test-current-row" in ids
    assert "test-historical-update" in update_ids
    assert "test-current-update" in update_ids

    with get_connection() as conn:
        conn.execute("DELETE FROM pickup_schedule WHERE id = ANY(%s)", (list(cleanup_schedule_ids),))
        conn.execute("DELETE FROM game_updates WHERE id = ANY(%s)", (list(cleanup_update_ids),))
        conn.commit()


def test_scraper_pickup_schedule_id_matches_seed_convention():
    rows = [
        {
            "banner": "Lucy: Whiteout",
            "four_stars": [],
            "start_year": 2026,
            "start_month": 7,
            "start_day": 1,
            "end_month": 7,
            "end_day": 21,
            "end_year": 2026,
        }
    ]

    schedule = content_refresh._schedule_from_banner_rows(rows)

    assert schedule[0]["id"] == "2026-07-first"
    assert schedule[0]["category"] == "first_pickup"

def test_official_updates_prefer_korean_articles_and_fallback_to_english(monkeypatch):
    korean_menu = {
        "article": [
            {
                "articleId": 4814,
                "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
                "startTime": "2026-06-08 10:00:00",
            }
        ]
    }
    english_menu = {
        "article": [
            {
                "articleId": 4973,
                "articleTitle": "Wuthering Waves Version 3.5 Update Maintenance Notice",
                "startTime": "2026-07-03 11:00:00",
            }
        ]
    }
    articles = {
        ("kr", 4814): {
            "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
            "startTime": "2026-06-08 10:00:00",
            "articleContent": "방랑자님 3.4 버전 내용 안내입니다. 점검 시간: 2026년 6월 8일 05:00 ~ 2026년 6월 8일 12:00 신규 캐릭터 루시 콜라보 콘텐츠",
        },
        ("en", 4973): {
            "articleTitle": "Wuthering Waves Version 3.5 Update Maintenance Notice",
            "startTime": "2026-07-03 11:00:00",
            "articleContent": "Version 3.5 Blade of Past Resounds, Lingering Dream Hymns. Maintenance Duration: 2026-07-10 04:00 - 2026-07-10 11:00 (UTC+8). Astrite x300.",
        },
    }

    def fake_fetch_official_json(locale: str, filename: str):
        if filename == "MainMenu.json":
            return korean_menu if locale == "kr" else english_menu
        article_id = int(filename.removeprefix("article/").removesuffix(".json"))
        return articles[(locale, article_id)]

    monkeypatch.setattr(content_refresh, "_fetch_official_json", fake_fetch_official_json)

    updates = content_refresh._updates_from_official_articles()

    assert [update["version"] for update in updates[:2]] == ["3.5", "3.4"]
    assert updates[0]["id"] == "wuwa-3-5"
    assert updates[0]["release_date_kst"] == "2026-07-10 05:00 KST"
    assert updates[0]["source_links"] == ["https://wutheringwaves.kurogames.com/en/main/news/detail/4973"]
    assert updates[0]["summary_ko"] == ""
    assert updates[1]["source_links"] == ["https://wutheringwaves.kurogames.com/kr/main/news/detail/4814"]
    assert updates[1]["summary_ko"] == ""



def test_official_updates_keep_records_since_2024_with_kst_datetime_and_no_summary(monkeypatch):
    korean_menu = {
        "article": [
            {
                "articleId": 951,
                "articleTitle": "『명조:워더링 웨이브』 1.1 버전 업데이트 점검사항 사전 공지",
                "startTime": "2024-06-25 12:30:00",
            }
        ]
    }
    english_menu = {
        "article": [
            {
                "articleId": 4973,
                "articleTitle": "Wuthering Waves Version 3.5 Update Maintenance Notice",
                "startTime": "2026-07-03 11:00:00",
            }
        ]
    }
    articles = {
        ("kr", 951): {
            "articleTitle": "『명조:워더링 웨이브』 1.1 버전 업데이트 점검사항 사전 공지",
            "startTime": "2024-06-25 12:30:00",
            "articleContent": "점검 시간: 2024년 6월 28일 05:00 ~ 2024년 6월 28일 12:00",
        },
        ("en", 4973): {
            "articleTitle": "Wuthering Waves Version 3.5 Update Maintenance Notice",
            "startTime": "2026-07-03 11:00:00",
            "articleContent": "Maintenance Duration: 2026-07-10 04:00 - 2026-07-10 11:00 (UTC+8)",
        },
    }

    def fake_fetch_official_json(locale: str, filename: str):
        if filename == "MainMenu.json":
            return korean_menu if locale == "kr" else english_menu
        article_id = int(filename.removeprefix("article/").removesuffix(".json"))
        return articles[(locale, article_id)]

    monkeypatch.setattr(content_refresh, "_fetch_official_json", fake_fetch_official_json)

    updates = content_refresh._updates_from_official_articles(since_year=2024)

    assert [update["version"] for update in updates] == ["3.5", "1.1"]
    assert updates[0]["release_date_kst"] == "2026-07-10 05:00 KST"
    assert updates[0]["summary_ko"] == ""
    assert updates[0]["highlights_ko"] == []
    assert updates[0]["source_links"] == ["https://wutheringwaves.kurogames.com/en/main/news/detail/4973"]
    assert updates[1]["release_date_kst"] == "2024-06-28 05:00 KST"
    assert updates[1]["source_links"] == ["https://wutheringwaves.kurogames.com/kr/main/news/detail/951"]


def test_extract_hero_image_url_finds_first_img():
    content = 'intro <p><img src="https://cdn.example/hero.jpg" alt="x" /></p> tail'
    assert content_refresh._extract_hero_image_url(content) == "https://cdn.example/hero.jpg"


def test_extract_hero_image_url_none_without_img():
    assert content_refresh._extract_hero_image_url("no images here") is None


def test_extract_thematic_title_strips_content_notice_suffix():
    title = "「선택하지 않은 꿈」 3.4 버전 내용 안내"
    assert content_refresh._extract_thematic_title(title, "3.4") == "「선택하지 않은 꿈」 3.4 버전"


def test_extract_thematic_title_falls_back_for_non_content_articles():
    title = "Wuthering Waves Version 3.5 Update Maintenance Notice"
    assert content_refresh._extract_thematic_title(title, "3.5") == "3.5 업데이트"


def test_extract_hero_image_url_handles_single_quotes():
    content = "intro <img src='https://cdn.example/hero.png' /> tail"
    assert content_refresh._extract_hero_image_url(content) == "https://cdn.example/hero.png"


def test_extract_hero_image_url_when_src_is_not_first_attribute():
    content = '<img alt="banner" src="https://cdn.example/hero2.jpg" />'
    assert content_refresh._extract_hero_image_url(content) == "https://cdn.example/hero2.jpg"


def test_extract_hero_image_url_returns_first_of_multiple():
    content = '<img src="https://cdn.example/first.jpg" /> mid <img src="https://cdn.example/second.jpg" />'
    assert content_refresh._extract_hero_image_url(content) == "https://cdn.example/first.jpg"


def test_official_updates_extract_title_and_image_source(monkeypatch):
    korean_menu = {
        "article": [
            {
                "articleId": 4814,
                "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
                "startTime": "2026-06-08 10:00:00",
            }
        ]
    }
    english_menu = {"article": []}
    articles = {
        ("kr", 4814): {
            "articleTitle": "「선택하지 않은 꿈」 3.4 버전 내용 안내",
            "startTime": "2026-06-08 10:00:00",
            "articleContent": (
                '방랑자님 <img src="https://cdn.example/hero-3-4.jpg" /> '
                "3.4 버전 내용 안내 점검 시간: 2026년 6월 8일 05:00"
            ),
        },
    }

    def fake_fetch_official_json(locale: str, filename: str):
        if filename == "MainMenu.json":
            return korean_menu if locale == "kr" else english_menu
        article_id = int(filename.removeprefix("article/").removesuffix(".json"))
        return articles[(locale, article_id)]

    monkeypatch.setattr(content_refresh, "_fetch_official_json", fake_fetch_official_json)

    updates = content_refresh._updates_from_official_articles()

    assert updates[0]["version"] == "3.4"
    assert updates[0]["title_ko"] == "「선택하지 않은 꿈」 3.4 버전"
    assert updates[0]["image_source_url"] == "https://cdn.example/hero-3-4.jpg"
    assert updates[0]["summary_ko"] == ""
