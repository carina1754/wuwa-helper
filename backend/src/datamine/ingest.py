from __future__ import annotations

from datetime import datetime, timezone

from ..database import get_connection
from .bindata import ingest_bindata
from .normalize import build_sim_character, build_sim_role_growth
from .schema import init_datamine_schema
from .textmap import ingest_textmap


def run_ingest() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            init_datamine_schema(cur)
        conn.commit()
        counts = {
            "bindata_rows": ingest_bindata(conn),
            "textmap_rows": ingest_textmap(conn),
            "role_growth": build_sim_role_growth(conn),
            "characters": build_sim_character(conn),
        }
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_state (source, refreshed_at, status, message)
                VALUES ('datamine', %s, 'ok', %s)
                ON CONFLICT (source) DO UPDATE SET
                    refreshed_at = EXCLUDED.refreshed_at,
                    status = EXCLUDED.status,
                    message = EXCLUDED.message
                """,
                (datetime.now(timezone.utc).isoformat(), str(counts)),
            )
        conn.commit()
    return counts


if __name__ == "__main__":
    print(run_ingest())
