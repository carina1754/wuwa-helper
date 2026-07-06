from __future__ import annotations

from .content_refresh import refresh_pickups_and_updates_if_stale
from .database import get_connection
from .models import GameUpdateSummary, PickupScheduleItem


def load_pickup_schedule(year: int | None = None) -> list[PickupScheduleItem]:
    refresh_pickups_and_updates_if_stale()
    query = "SELECT data_json FROM pickup_schedule"
    params: tuple[int, ...] = ()
    if year is not None:
        query += " WHERE year = ?"
        params = (year,)
    query += (
        " ORDER BY year DESC, month ASC,"
        " CASE category"
        " WHEN 'first_pickup' THEN 1"
        " WHEN 'rerun_1' THEN 2"
        " WHEN 'rerun_2' THEN 3"
        " WHEN 'rerun_3' THEN 4"
        " ELSE 5"
        " END"
    )
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [PickupScheduleItem.model_validate_json(row["data_json"]) for row in rows]


def load_game_updates() -> list[GameUpdateSummary]:
    refresh_pickups_and_updates_if_stale()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT data_json
            FROM game_updates
            ORDER BY release_date_kst DESC, version DESC
            """
        ).fetchall()
    return [GameUpdateSummary.model_validate_json(row["data_json"]) for row in rows]
