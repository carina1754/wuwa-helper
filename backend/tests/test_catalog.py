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
