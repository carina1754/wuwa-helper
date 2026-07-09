from __future__ import annotations

from src.datamine.bindata import ingest_bindata
from src.datamine.normalize import build_sim_character, build_sim_role_growth
from src.datamine.textmap import ingest_textmap


def test_build_sim_role_growth(conn):
    ingest_bindata(conn)
    n = build_sim_role_growth(conn)
    assert n == 2
    with conn.cursor() as cur:
        cur.execute(
            "SELECT atk_ratio, def_ratio, hp_ratio FROM sim_role_growth WHERE level = 90 AND breach = 6"
        )
        row = cur.fetchone()
    assert row["atk_ratio"] == 125000
    assert row["def_ratio"] == 122222
    assert row["hp_ratio"] == 125000


def test_build_sim_character_hiyuki(conn):
    ingest_bindata(conn)
    ingest_textmap(conn)
    n = build_sim_character(conn)
    assert n == 1  # 트라이얼/저레어 9999는 제외

    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sim_character WHERE id = 1108")
        c = cur.fetchone()
    assert c["name_ko"] == "히유키"
    assert c["name_en"] == "Hiyuki"
    assert c["rarity"] == 5
    assert c["element_id"] == 1
    assert c["element_ko"] == "응결"
    assert c["weapon_type"] == 2
    assert c["weapon_type_ko"] == "직검"
    assert c["base_atk"] == 37
    assert c["base_def"] == 91
    assert c["base_crit"] == 5.0
    assert c["base_crit_dmg"] == 150.0
    assert c["skill_id"] == 1108
    assert c["resonant_chain_group_id"] == 1108


def test_sim_character_lv90_atk_matches_phro(conn):
    ingest_bindata(conn)
    ingest_textmap(conn)
    build_sim_role_growth(conn)
    build_sim_character(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT base_atk FROM sim_character WHERE id = 1108")
        base_atk = cur.fetchone()["base_atk"]
        cur.execute("SELECT atk_ratio FROM sim_role_growth WHERE level = 90 AND breach = 6")
        ratio = cur.fetchone()["atk_ratio"]
    lv90_atk = base_atk * ratio / 10000.0
    assert lv90_atk == 462.5  # phro 히유키 캐릭 base ATK와 일치
