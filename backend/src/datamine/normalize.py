from __future__ import annotations

from psycopg import Connection


def _bindata_rows(conn: Connection, table_name: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT data FROM datamine_bindata WHERE table_name = %s", (table_name,))
        return [r["data"] for r in cur.fetchall()]


def build_sim_role_growth(conn: Connection) -> int:
    rows = _bindata_rows(conn, "property/rolepropertygrowth")
    n = 0
    with conn.cursor() as cur:
        for d in rows:
            cur.execute(
                """
                INSERT INTO sim_role_growth (level, breach, atk_ratio, def_ratio, hp_ratio)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (level, breach) DO UPDATE SET
                    atk_ratio = EXCLUDED.atk_ratio,
                    def_ratio = EXCLUDED.def_ratio,
                    hp_ratio = EXCLUDED.hp_ratio
                """,
                (d["Level"], d["BreachLevel"], d["AtkRatio"], d["DefRatio"], d["LifeMaxRatio"]),
            )
            n += 1
    conn.commit()
    return n
