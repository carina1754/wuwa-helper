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


def test_refresh_characters_uses_curated_role_map(monkeypatch):
    """A curated role in the static _CURATED_ROLE map is applied by game id."""
    init_db()
    fixture = (
        '[{"Id":99990001,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"Element":{"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    # 99990001 is a sentinel id, never in the real map; inject a curated role.
    monkeypatch.setitem(refresh._CURATED_ROLE, 99990001, "support")
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()
    try:
        refresh.refresh_characters(
            fetch=lambda kind: fixture,
            cache=lambda kind, cat, asset: None,
        )
        with get_connection() as c:
            row = c.execute(
                "SELECT role, data_json FROM wuwa_resonator WHERE id=%s", (99990001,)
            ).fetchone()
        assert row["role"] == "support"  # curated role from the static map
        assert json.loads(row["data_json"])["role"] == "support"
    finally:
        with get_connection() as c:
            c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
            c.commit()


def test_refresh_characters_defaults_role_when_not_in_map():
    """A resonator whose id is absent from _CURATED_ROLE defaults to main_dps."""
    init_db()
    fixture = (
        '[{"Id":99990001,"Name":"카멜리아","NameEn":"Camellya","QualityId":5,'
        '"Element":{"Name":"인멸"},"WeaponType":2,"RoleType":1,'
        '"RoleHeadIconBig":"T_x.png","Skills":[],"ResonantChainGroup":[],'
        '"Ascension":[],"Stats":{}}]'
    )
    assert 99990001 not in refresh._CURATED_ROLE  # sentinel id is never curated
    with get_connection() as c:
        c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
        c.commit()
    try:
        refresh.refresh_characters(
            fetch=lambda kind: fixture,
            cache=lambda kind, cat, asset: None,
        )
        with get_connection() as c:
            row = c.execute(
                "SELECT role, data_json FROM wuwa_resonator WHERE id=%s", (99990001,)
            ).fetchone()
        assert row["role"] == "main_dps"  # default when id not in the map
        assert json.loads(row["data_json"])["role"] == "main_dps"
    finally:
        with get_connection() as c:
            c.execute("DELETE FROM wuwa_resonator WHERE id=%s", (99990001,))
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
    assert e["rarity"] == 0  # from the RAW "Rarity" field (0-3), not QualityId (const 2)
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
    # refresh_echoes() reconciles (full-replace: deletes rows not in the fetched
    # set), so save + restore the whole echo table around this 1-fixture refresh
    # to avoid wiping the shared dev DB's real echoes.
    with get_connection() as c:
        saved = c.execute(
            "SELECT id, name_ko, name_en, cost, rarity, data_json FROM wuwa_echo"
        ).fetchall()
    try:
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
        assert row["rarity"] == 0  # RAW "Rarity" field, not QualityId
        d = json.loads(row["data_json"])
        assert d["icon"] == "/catalog/image/echoes/e"
        assert d["sonata"] == ["울려퍼지는 뇌음"]
        assert d["source"] == "wuthering.gg"
    finally:
        with get_connection() as c:
            c.execute("DELETE FROM wuwa_echo")
            for r in saved:
                c.execute(
                    "INSERT INTO wuwa_echo (id, name_ko, name_en, cost, rarity, data_json, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, now())",
                    (r["id"], r["name_ko"], r["name_en"], r["cost"], r["rarity"], r["data_json"]),
                )
            c.commit()
