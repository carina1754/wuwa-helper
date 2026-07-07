import json

from src.database import get_connection, init_db
from src.wutheringgg import refresh
from src.wutheringgg.normalize import normalize_echo, normalize_weapon

# Real captured weapon object (live chunk CaGhi8-P.js), trimmed, with a sentinel
# test-only Id so cleanup never touches real game data.
RAW_WEAPON = {
    "Id": "zzz-test-weapon",
    "WeaponName": "푸른물결의 빛",
    "WeaponNameEn": "Lustrous Razor",
    "WeaponType": 1,
    "QualityId": 5,
    "Icon": "T_IconWeapon21010015_UI.png",
    "Desc": "d",
    "AttributesDescription": "attr",
    "TypeDescription": "type",
    "Resonance": [{"x": 1}],
    "Ascension": [],
}

# Real captured echo object (live chunk BcbUvbl9.js), trimmed, with a sentinel
# test-only Id so cleanup never touches real game data.
RAW_ECHO = {
    "Id": "zzz-test-echo",
    "MonsterName": "뇌운의 비늘",
    "MonsterNameEn": "Thundering Mephis",
    "Cost": 4,
    "QualityId": 2,
    "Rarity": 0,
    "PhantomType": 1,
    "IconMiddle": "T_IconMonsterGoods160_222_UI.png",
    "IconBig": "/Game/Aki/UI/.../T_IconMonsterHead732_x_UI",
    "Skill": {"Name": "sk"},
    "MainProp": {"RandGroupId": 1},
    "Desc": "d",
    "FetterGroup": [{"FetterGroupName": "울려퍼지는 뇌음", "Id": 3}],
}


def test_refresh_characters_upserts(monkeypatch):
    init_db()
    fixture = (
        '[{"Id":99990001,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"ElementId":6,"Element":{"Id":6,"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()
    n = refresh.refresh_characters(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: f"/catalog/image/{kind}/x",
    )
    assert n == 1
    with get_connection() as c:
        row = c.execute(
            "SELECT name_ko, name_en, element, weapon_type, rarity, data_json "
            "FROM wuwa_resonator WHERE id=%s",
            (99990001,),
        ).fetchone()
    assert row["name_ko"] == "카멜리아"
    assert row["name_en"] == "Camellya"
    assert row["element"] == "인멸"
    assert row["weapon_type"] == "Sword"
    assert row["rarity"] == 5
    d = json.loads(row["data_json"])
    assert d["name"] == "카멜리아" and d["weapon_type"] == "Sword"
    assert d["image"] == "/catalog/image/characters/x"
    assert d["source"] == "wuthering.gg"
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()


def test_refresh_characters_carries_over_catalog_role(monkeypatch):
    """A curated role in character_catalog is carried into wuwa_resonator by id."""
    init_db()
    fixture = (
        '[{"Id":99990001,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"Element":{"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()
    # Snapshot any pre-existing catalog row so the shared dev DB is left intact.
    with get_connection() as c:
        existing = c.execute(
            "SELECT id, name, element, weapon_type, rarity, role, data_json, source "
            "FROM character_catalog WHERE id=%s",
            (99990001,),
        ).fetchone()
    try:
        with get_connection() as c:
            c.execute("DELETE FROM character_catalog WHERE id=%s", (99990001,))
            c.execute(
                "INSERT INTO character_catalog (id, name, role, data_json) "
                "VALUES (%s, %s, %s, %s)",
                (99990001, "카멜리아", "support", "{}"),
            )
            c.commit()
        refresh.refresh_characters(
            fetch=lambda kind: fixture,
            cache=lambda kind, cat, asset: None,
        )
        with get_connection() as c:
            row = c.execute(
                "SELECT role, data_json FROM wuwa_resonator WHERE id=%s", (99990001,)
            ).fetchone()
        assert row["role"] == "support"  # curated role carried over
        assert json.loads(row["data_json"])["role"] == "support"
    finally:
        with get_connection() as c:
            c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
            c.execute("DELETE FROM character_catalog WHERE id=%s", (99990001,))
            if existing is not None:
                c.execute(
                    "INSERT INTO character_catalog "
                    "(id, name, element, weapon_type, rarity, role, data_json, source) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        existing["id"],
                        existing["name"],
                        existing["element"],
                        existing["weapon_type"],
                        existing["rarity"],
                        existing["role"],
                        existing["data_json"],
                        existing["source"],
                    ),
                )
            c.commit()


def test_refresh_characters_defaults_role_when_no_catalog_row(monkeypatch):
    """A resonator with no matching character_catalog row defaults to main_dps."""
    init_db()
    fixture = (
        '[{"Id":99990001,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"Element":{"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()
    # Snapshot + remove any catalog row so id=99990001 truly has no catalog entry.
    with get_connection() as c:
        existing = c.execute(
            "SELECT id, name, element, weapon_type, rarity, role, data_json, source "
            "FROM character_catalog WHERE id=%s",
            (99990001,),
        ).fetchone()
    try:
        with get_connection() as c:
            c.execute("DELETE FROM character_catalog WHERE id=%s", (99990001,))
            c.commit()
        refresh.refresh_characters(
            fetch=lambda kind: fixture,
            cache=lambda kind, cat, asset: None,
        )
        with get_connection() as c:
            row = c.execute(
                "SELECT role, data_json FROM wuwa_resonator WHERE id=%s", (99990001,)
            ).fetchone()
        assert row["role"] == "main_dps"  # default when no catalog row
        assert json.loads(row["data_json"])["role"] == "main_dps"
    finally:
        with get_connection() as c:
            c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
            if existing is not None:
                c.execute(
                    "INSERT INTO character_catalog "
                    "(id, name, element, weapon_type, rarity, role, data_json, source) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        existing["id"],
                        existing["name"],
                        existing["element"],
                        existing["weapon_type"],
                        existing["rarity"],
                        existing["role"],
                        existing["data_json"],
                        existing["source"],
                    ),
                )
            c.commit()


# --- Task 7: weapons + echoes ------------------------------------------------


def test_normalize_weapon():
    w = normalize_weapon(RAW_WEAPON)
    assert w["id"] == "zzz-test-weapon"  # game Id as TEXT (wuwa_weapon.id is TEXT)
    assert w["name_ko"] == "푸른물결의 빛"
    assert w["name_en"] == "Lustrous Razor"
    assert w["weapon_type"] == "Broadsword"
    assert w["weapon_type_ko"] == "대검"
    assert w["rarity"] == 5
    assert w["icon_asset"] == "T_IconWeapon21010015_UI.png"
    assert w["resonance"] == [{"x": 1}]


def test_normalize_echo():
    e = normalize_echo(RAW_ECHO)
    assert e["id"] == "zzz-test-echo"  # game Id as TEXT (wuwa_echo.id is TEXT)
    assert e["name_ko"] == "뇌운의 비늘"
    assert e["name_en"] == "Thundering Mephis"
    assert e["cost"] == 4
    assert e["rarity"] == 2
    assert e["phantom_type"] == 1
    assert e["icon_asset"] == "T_IconMonsterGoods160_222_UI.png"
    assert e["sonata"] == ["울려퍼지는 뇌음"]
    assert e["skill"] == {"Name": "sk"}


def test_refresh_weapons_upserts():
    init_db()
    fixture = json.dumps([RAW_WEAPON], ensure_ascii=False)
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_weapon WHERE id=%s", ("zzz-test-weapon",))
        c.commit()
    n = refresh.refresh_weapons(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: f"/catalog/image/{kind}/w",
    )
    assert n == 1
    with get_connection() as c:
        row = c.execute(
            "SELECT name_ko, name_en, weapon_type, rarity, data_json "
            "FROM wuwa_weapon WHERE id=%s",
            ("zzz-test-weapon",),
        ).fetchone()
    assert row["name_ko"] == "푸른물결의 빛"
    assert row["name_en"] == "Lustrous Razor"
    assert row["weapon_type"] == "Broadsword"
    assert row["rarity"] == 5
    d = json.loads(row["data_json"])
    assert d["icon"] == "/catalog/image/weapons/w"
    assert d["name_en"] == "Lustrous Razor"
    assert d["source"] == "wuthering.gg"
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_weapon WHERE id=%s", ("zzz-test-weapon",))
        c.commit()


def test_refresh_echoes_upserts():
    init_db()
    fixture = json.dumps([RAW_ECHO], ensure_ascii=False)
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_echo WHERE id=%s", ("zzz-test-echo",))
        c.commit()
    n = refresh.refresh_echoes(
        fetch=lambda kind: fixture,
        cache=lambda kind, cat, asset: f"/catalog/image/{kind}/e",
    )
    assert n == 1
    with get_connection() as c:
        row = c.execute(
            "SELECT name_ko, name_en, cost, rarity, data_json FROM wuwa_echo WHERE id=%s",
            ("zzz-test-echo",),
        ).fetchone()
    assert row["name_ko"] == "뇌운의 비늘"
    assert row["name_en"] == "Thundering Mephis"
    assert row["cost"] == 4
    assert row["rarity"] == 2
    d = json.loads(row["data_json"])
    assert d["icon"] == "/catalog/image/echoes/e"
    assert d["sonata"] == ["울려퍼지는 뇌음"]
    assert d["source"] == "wuthering.gg"
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_echo WHERE id=%s", ("zzz-test-echo",))
        c.commit()
