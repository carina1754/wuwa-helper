import json

from src.database import get_connection, init_db
from src.wutheringgg import refresh


def test_refresh_characters_upserts(monkeypatch):
    init_db()
    fixture = (
        '[{"Id":1603,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"ElementId":6,"Element":{"Id":6,"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,))
        c.commit()
    n = refresh.refresh_characters(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: f"/catalog/image/{kind}/x",
    )
    assert n == 1
    with get_connection() as c:
        row = c.execute(
            "SELECT data_json FROM character_catalog WHERE id=%s", (1603,)
        ).fetchone()
    d = json.loads(row["data_json"])
    assert d["name"] == "카멜리아" and d["weapon_type"] == "Sword"
    assert d["image"] == "/catalog/image/characters/x"
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,))
        c.commit()


def test_refresh_characters_preserves_existing_role(monkeypatch):
    init_db()
    fixture = (
        '[{"Id":1603,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"Element":{"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,))
        c.execute(
            "INSERT INTO character_catalog (id, name, role, data_json) "
            "VALUES (%s, %s, %s, %s)",
            (1603, "카멜리아", "support", "{}"),
        )
        c.commit()
    refresh.refresh_characters(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: None,
    )
    with get_connection() as c:
        row = c.execute(
            "SELECT role, data_json FROM character_catalog WHERE id=%s", (1603,)
        ).fetchone()
    assert row["role"] == "support"  # pre-existing role preserved
    assert json.loads(row["data_json"])["role"] == "support"
    with get_connection() as c:
        c.execute("DELETE FROM character_catalog WHERE id=%s", (1603,))
        c.commit()
