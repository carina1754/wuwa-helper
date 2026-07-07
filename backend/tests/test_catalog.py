from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from src import catalog
from src.database import get_connection, init_db

client = TestClient(app)


def test_weapon_id_is_stable_and_safe():
    a = catalog.weapon_id("스펙트럴 트리거")
    assert a == catalog.weapon_id("스펙트럴 트리거")
    assert catalog.weapon_id("A") != catalog.weapon_id("B")
    assert a.replace("-", "").replace("w", "", 1).isalnum()  # url/fs safe


def test_refresh_and_load_weapon_catalog(monkeypatch):
    init_db()
    monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")
    monkeypatch.setattr(
        catalog,
        "parse_weapons",
        lambda html: [
            {"name_ko": "테스트권총", "weapon_type": "권총", "rarity": 5, "icon_source": "https://x/a.webp"}
        ],
    )
    monkeypatch.setattr(
        catalog, "ensure_catalog_image", lambda kind, wid, src: f"/catalog/image/{kind}/{wid}"
    )
    wid = catalog.weapon_id("테스트권총")
    with get_connection() as conn:
        conn.execute("DELETE FROM weapon_catalog WHERE id = %s", (wid,))
        conn.commit()

    assert catalog.refresh_weapon_catalog() == 1
    item = next(w for w in catalog.load_weapon_catalog() if w.id == wid)
    assert item.name_ko == "테스트권총"
    assert item.weapon_type == "권총"
    assert item.rarity == 5
    assert item.icon == f"/catalog/image/weapons/{wid}"

    with get_connection() as conn:
        conn.execute("DELETE FROM weapon_catalog WHERE id = %s", (wid,))
        conn.commit()


def test_catalog_image_route_serves_cached_file(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    weapons_dir = tmp_path / "weapons"
    weapons_dir.mkdir(parents=True)
    (weapons_dir / "w-abc123.webp").write_bytes(b"iconbytes")
    response = client.get("/catalog/image/weapons/w-abc123")
    assert response.status_code == 200
    assert response.content == b"iconbytes"


def test_catalog_image_route_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert client.get("/catalog/image/weapons/does-not-exist").status_code == 404


def test_catalog_image_route_rejects_unknown_kind(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert client.get("/catalog/image/evil/x").status_code == 404


def test_refresh_character_kits_stores_and_loads(monkeypatch):
    init_db()
    monkeypatch.setattr(catalog, "CHARACTER_NAMES", ["테스트캐릭"])
    monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")
    monkeypatch.setattr(
        catalog.namu_characters,
        "parse_character",
        lambda html: {"name_ko": "테스트캐릭", "element": "회절", "skills": [{"slot": "기본 공격"}]},
    )
    cid = catalog._hash_id("c-", "테스트캐릭")
    with get_connection() as conn:
        conn.execute("DELETE FROM character_kit WHERE id = %s", (cid,))
        conn.commit()

    assert catalog.refresh_character_kits() == 1
    kit = next(k for k in catalog.load_character_kits() if k["name_ko"] == "테스트캐릭")
    assert kit["element"] == "회절"
    assert kit["id"] == cid

    with get_connection() as conn:
        conn.execute("DELETE FROM character_kit WHERE id = %s", (cid,))
        conn.commit()


def test_refresh_echo_catalog_stores_sonata_and_echoes(monkeypatch):
    init_db()
    monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")
    monkeypatch.setattr(catalog, "_ECHO_TIER_PAGES", ["해일급"])
    monkeypatch.setattr(
        catalog.namu_echoes,
        "parse_sonata_sets",
        lambda html: [{"name_ko": "테스트소나타", "two_piece": "x", "icon": "https://i/s.webp"}],
    )
    monkeypatch.setattr(
        catalog.namu_echoes,
        "parse_echoes",
        lambda html, sonata=None: [{"name_ko": "테스트에코", "cost": 4, "icon": "https://i/e.webp"}],
    )
    monkeypatch.setattr(
        catalog, "ensure_catalog_image", lambda kind, item_id, src: f"/catalog/image/{kind}/{item_id}"
    )
    sid = catalog._hash_id("s-", "테스트소나타")
    eid = catalog._hash_id("e-", "테스트에코")
    with get_connection() as conn:
        conn.execute("DELETE FROM sonata_set WHERE id = %s", (sid,))
        conn.execute("DELETE FROM echo_catalog WHERE id = %s", (eid,))
        conn.commit()

    assert catalog.refresh_echo_catalog() == 2
    assert any(s["name_ko"] == "테스트소나타" for s in catalog.load_sonata_sets())
    echo = next(e for e in catalog.load_echoes() if e["name_ko"] == "테스트에코")
    assert echo["cost"] == 4
    assert echo["icon"] == f"/catalog/image/echoes/{eid}"

    with get_connection() as conn:
        conn.execute("DELETE FROM sonata_set WHERE id = %s", (sid,))
        conn.execute("DELETE FROM echo_catalog WHERE id = %s", (eid,))
        conn.commit()


def test_data_endpoints_return_lists():
    assert isinstance(client.get("/character-kits").json(), list)
    assert isinstance(client.get("/echoes").json(), list)
    assert isinstance(client.get("/sonata-sets").json(), list)
    assert isinstance(client.get("/pickup-banners").json(), list)


def test_refresh_pickup_banners_merges_char_and_weapon(monkeypatch):
    from src.models import WeaponCatalogItem

    init_db()
    # refresh_pickup_banners() full-replaces the table; save real rows so this
    # test never wipes the app's crawled data in the shared dev DB.
    with get_connection() as conn:
        saved = conn.execute("SELECT id, version, phase, data_json FROM pickup_banners").fetchall()

    try:
        monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")

        def fake_banners(html, kind):
            if kind == "character":
                return [
                    {
                        "version": "9.9", "phase": 1, "banner_name": "테스트배너", "is_rerun": False,
                        "items": ["테스트캐릭"], "start_date": "2099-01-01", "end_date": "2099-01-15",
                        "icons": [{"alt": "명조 9.9 테스트캐릭", "src": "https://i/c.webp"}],
                    }
                ]
            return [{"version": "9.9", "phase": 1, "items": ["테스트권총"], "icons": []}]

        monkeypatch.setattr(catalog, "parse_banner_history", fake_banners)
        monkeypatch.setattr(
            catalog, "ensure_catalog_image", lambda kind, iid, src: f"/catalog/image/{kind}/{iid}" if src else None
        )
        monkeypatch.setattr(
            catalog,
            "load_weapon_catalog",
            lambda: [WeaponCatalogItem(id="w-x", name_ko="테스트권총", weapon_type="권총", rarity=5,
                                       icon="/catalog/image/weapons/w-x")],
        )

        assert catalog.refresh_pickup_banners() == 1
        banner = next(b for b in catalog.load_pickup_banners() if b.version == "9.9")
        assert banner.characters[0].name_ko == "테스트캐릭"
        assert banner.characters[0].avatar == f"/catalog/image/characters/{catalog._hash_id('c-', '테스트캐릭')}"
        assert banner.weapons[0].name_ko == "테스트권총"
        assert banner.weapons[0].icon == "/catalog/image/weapons/w-x"
        assert banner.weapons[0].rarity == 5
    finally:
        with get_connection() as conn:
            conn.execute("DELETE FROM pickup_banners")
            for row in saved:
                conn.execute(
                    "INSERT INTO pickup_banners (id, version, phase, data_json, updated_at) VALUES (%s, %s, %s, %s, now())",
                    (row["id"], row["version"], row["phase"], row["data_json"]),
                )
            conn.commit()


def test_refresh_pickup_banners_prefers_catalog_image(monkeypatch):
    """A pickup character mapped to a character_catalog entry reuses the
    planner's cached small image instead of the Namuwiki banner avatar."""
    import json as _json

    init_db()
    with get_connection() as conn:
        saved = conn.execute("SELECT id, version, phase, data_json FROM pickup_banners").fetchall()
        conn.execute("DELETE FROM character_catalog WHERE id = %s", (777777,))
        conn.execute(
            "INSERT INTO character_catalog (id, name, role, data_json, updated_at) VALUES (%s, %s, %s, %s, now())",
            (
                777777, "TestCatChar", "main_dps",
                _json.dumps(
                    {"id": 777777, "name": "TestCatChar", "role": "main_dps",
                     "image": "/catalog/image/characters/cat-777777"},
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    try:
        monkeypatch.setattr(catalog, "PICKUP_NAME_TO_CATALOG", {"테스트캐릭": "TestCatChar"})
        monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")

        def fake_banners(html, kind):
            if kind == "character":
                return [{
                    "version": "9.9", "phase": 1, "banner_name": "b", "is_rerun": False,
                    "items": ["테스트캐릭"], "start_date": None, "end_date": None,
                    "icons": [{"alt": "명조 9.9 테스트캐릭", "src": "https://i/c.webp"}],
                }]
            return []

        monkeypatch.setattr(catalog, "parse_banner_history", fake_banners)
        monkeypatch.setattr(catalog, "load_weapon_catalog", lambda: [])
        # If the mapping worked this must NOT be called; make it loud if it is.
        monkeypatch.setattr(
            catalog, "ensure_catalog_image",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should use catalog image")),
        )

        assert catalog.refresh_pickup_banners() == 1
        banner = next(b for b in catalog.load_pickup_banners() if b.version == "9.9")
        assert banner.characters[0].avatar == "/catalog/image/characters/cat-777777"
    finally:
        with get_connection() as conn:
            conn.execute("DELETE FROM character_catalog WHERE id = %s", (777777,))
            conn.execute("DELETE FROM pickup_banners")
            for row in saved:
                conn.execute(
                    "INSERT INTO pickup_banners (id, version, phase, data_json, updated_at) VALUES (%s, %s, %s, %s, now())",
                    (row["id"], row["version"], row["phase"], row["data_json"]),
                )
            conn.commit()


def test_refresh_character_catalog_images_rewrites_to_local(monkeypatch):
    import json as _json

    init_db()
    monkeypatch.setattr(catalog, "ensure_catalog_image", lambda kind, iid, src: f"/catalog/image/{kind}/{iid}")
    with get_connection() as conn:
        conn.execute("DELETE FROM character_catalog WHERE id = %s", (999999,))
        conn.execute(
            "INSERT INTO character_catalog (id, name, role, data_json, updated_at) VALUES (%s, %s, %s, %s, now())",
            (
                999999, "테스트", "main_dps",
                _json.dumps(
                    {"id": 999999, "name": "테스트", "role": "main_dps",
                     "image": "https://cdn.example/x.webp", "splash_image": "https://cdn.example/y.webp"},
                    ensure_ascii=False,
                ),
            ),
        )
        conn.commit()

    assert catalog.refresh_character_catalog_images() >= 1
    with get_connection() as conn:
        row = conn.execute("SELECT data_json FROM character_catalog WHERE id = %s", (999999,)).fetchone()
    data = _json.loads(row["data_json"])
    assert data["image"] == "/catalog/image/characters/cat-999999"
    assert data["splash_image"] == "/catalog/image/characters/cat-999999-splash"

    with get_connection() as conn:
        conn.execute("DELETE FROM character_catalog WHERE id = %s", (999999,))
        conn.commit()
