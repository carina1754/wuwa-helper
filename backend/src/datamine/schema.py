from __future__ import annotations

DATAMINE_DDL: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS datamine_bindata (
        table_name TEXT NOT NULL,
        row_id TEXT NOT NULL,
        data JSONB NOT NULL,
        PRIMARY KEY (table_name, row_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS datamine_textmap (
        lang TEXT NOT NULL,
        category TEXT NOT NULL,
        text_id TEXT NOT NULL,
        content TEXT NOT NULL,
        PRIMARY KEY (lang, category, text_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sim_role_growth (
        level INTEGER NOT NULL,
        breach INTEGER NOT NULL,
        atk_ratio INTEGER NOT NULL,
        def_ratio INTEGER NOT NULL,
        hp_ratio INTEGER NOT NULL,
        PRIMARY KEY (level, breach)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sim_character (
        id INTEGER PRIMARY KEY,
        name_ko TEXT,
        name_en TEXT,
        rarity INTEGER,
        element_id INTEGER,
        element_ko TEXT,
        weapon_type INTEGER,
        weapon_type_ko TEXT,
        max_level INTEGER,
        base_atk DOUBLE PRECISION,
        base_hp DOUBLE PRECISION,
        base_def DOUBLE PRECISION,
        base_crit DOUBLE PRECISION,
        base_crit_dmg DOUBLE PRECISION,
        skill_id INTEGER,
        skill_tree_group_id INTEGER,
        resonant_chain_group_id INTEGER,
        data_json TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_datamine_textmap_lookup ON datamine_textmap(lang, text_id)",
]


def init_datamine_schema(cur) -> None:
    for ddl in DATAMINE_DDL:
        cur.execute(ddl)
