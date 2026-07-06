from __future__ import annotations

import json
from pathlib import Path

from src.database import get_connection, init_db
from src.models import BuildRule, CharacterCatalogItem, GameUpdateSummary, PickupScheduleItem, SiteUpdateEntry, TeamRule
from src.rules import save_build_rules, save_character_catalog, save_team_rules

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def _load_json(filename: str) -> list[dict[str, object]]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _upsert_pickup_schedule(items: list[PickupScheduleItem]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
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
                    (item.id, item.year, item.month, item.category, item.model_dump_json()),
                )
        conn.commit()


def _upsert_game_updates(items: list[GameUpdateSummary]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO game_updates (id, version, release_date_kst, data_json, updated_at)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE SET
                        version = EXCLUDED.version,
                        release_date_kst = EXCLUDED.release_date_kst,
                        data_json = EXCLUDED.data_json,
                        updated_at = now()
                    """,
                    (item.id, item.version, item.release_date_kst, item.model_dump_json()),
                )
        conn.commit()


def _upsert_site_updates(items: list[SiteUpdateEntry]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO site_updates (id, date, version, title_ko, description_ko, data_json, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE SET
                        date = EXCLUDED.date,
                        version = EXCLUDED.version,
                        title_ko = EXCLUDED.title_ko,
                        description_ko = EXCLUDED.description_ko,
                        data_json = EXCLUDED.data_json,
                        updated_at = now()
                    """,
                    (item.id, item.date, item.version, item.title_ko, item.description_ko, item.model_dump_json()),
                )
        conn.commit()


def main() -> None:
    init_db()
    rules = [BuildRule.model_validate(item) for item in _load_json("build_rules.json")]
    team_rules = [TeamRule.model_validate(item) for item in _load_json("team_rules.json")]
    characters = [CharacterCatalogItem.model_validate(item) for item in _load_json("character_catalog.json")]
    pickup_schedule = [PickupScheduleItem.model_validate(item) for item in _load_json("pickup_schedule.json")]
    game_updates = [GameUpdateSummary.model_validate(item) for item in _load_json("game_updates.json")]
    site_updates = [SiteUpdateEntry.model_validate(item) for item in _load_json("site_updates.json")]

    if rules:
        save_build_rules(rules)
    if team_rules:
        save_team_rules(team_rules)
    if characters:
        save_character_catalog(characters)
    if pickup_schedule:
        _upsert_pickup_schedule(pickup_schedule)
    if game_updates:
        _upsert_game_updates(game_updates)
    if site_updates:
        _upsert_site_updates(site_updates)

    print(
        "Imported seed data: "
        f"rules={len(rules)} team_rules={len(team_rules)} characters={len(characters)} "
        f"pickup_schedule={len(pickup_schedule)} game_updates={len(game_updates)} site_updates={len(site_updates)}"
    )


if __name__ == "__main__":
    main()