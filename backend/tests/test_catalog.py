from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from src import catalog
from src.database import get_connection, init_db

client = TestClient(app)


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


def test_refresh_sonata_sets_stores_sets(monkeypatch):
    init_db()
    monkeypatch.setattr(catalog, "fetch_page", lambda title: "<html/>")
    monkeypatch.setattr(
        catalog.namu_echoes,
        "parse_sonata_sets",
        lambda html: [{"name_ko": "테스트소나타", "two_piece": "x", "icon": "https://i/s.webp"}],
    )
    monkeypatch.setattr(
        catalog, "ensure_catalog_image", lambda kind, item_id, src: f"/catalog/image/{kind}/{item_id}"
    )
    sid = catalog._hash_id("s-", "테스트소나타")
    with get_connection() as conn:
        conn.execute("DELETE FROM sonata_set WHERE id = %s", (sid,))
        conn.commit()

    assert catalog.refresh_sonata_sets() == 1
    sset = next(s for s in catalog.load_sonata_sets() if s["name_ko"] == "테스트소나타")
    assert sset["id"] == sid
    assert sset["icon"] == f"/catalog/image/echoes/{sid}"

    with get_connection() as conn:
        conn.execute("DELETE FROM sonata_set WHERE id = %s", (sid,))
        conn.commit()


def test_data_endpoints_return_lists():
    assert isinstance(client.get("/sonata-sets").json(), list)
    assert isinstance(client.get("/pickup-banners").json(), list)


def _save_pickup(conn):
    return conn.execute("SELECT id, version, phase, data_json FROM pickup_banners").fetchall()


def _restore_pickup(conn, saved):
    conn.execute("DELETE FROM pickup_banners")
    for row in saved:
        conn.execute(
            "INSERT INTO pickup_banners (id, version, phase, data_json, updated_at) VALUES (%s, %s, %s, %s, now())",
            (row["id"], row["version"], row["phase"], row["data_json"]),
        )
    conn.commit()


def test_refresh_pickup_banners_merges_char_and_weapon(monkeypatch):
    init_db()
    # refresh_pickup_banners() full-replaces the table; save real rows so this
    # test never wipes the app's crawled data in the shared dev DB.
    with get_connection() as conn:
        saved = _save_pickup(conn)

    try:
        def fake_all(page, kind):
            if kind == "character":
                return [
                    {
                        "version": "9.9", "phase": 1, "banner_name": "테스트배너", "is_rerun": False,
                        "items": ["테스트캐릭"], "start_date": "2099-01-01", "end_date": "2099-01-15",
                        "icons": [{"alt": "명조 9.9 테스트캐릭", "src": "https://i/c.webp"}],
                    }
                ]
            return [{"version": "9.9", "phase": 1, "items": ["테스트권총"], "icons": []}]

        monkeypatch.setattr(catalog, "_all_banner_history", fake_all)
        monkeypatch.setattr(catalog, "_collab_banner_history", lambda page, kind: [])
        # No resonator match -> avatar falls back to the crawled banner icon.
        monkeypatch.setattr(catalog, "_resonator_by_name", lambda: {})
        monkeypatch.setattr(
            catalog, "_weapon_by_name",
            lambda: {"테스트권총": {"icon": "/catalog/image/weapons/w-x", "rarity": 5, "weapon_type": "권총"}},
        )
        monkeypatch.setattr(
            catalog, "ensure_catalog_image", lambda kind, iid, src: f"/catalog/image/{kind}/{iid}" if src else None
        )

        assert catalog.refresh_pickup_banners() == 1
        banner = next(b for b in catalog.load_pickup_banners() if b.version == "9.9")
        assert len(banner.characters) == 1  # each era crawled once, no double-count
        assert banner.characters[0].name_ko == "테스트캐릭"
        assert banner.characters[0].avatar == f"/catalog/image/characters/{catalog._hash_id('c-', '테스트캐릭')}"
        assert banner.weapons[0].name_ko == "테스트권총"
        assert banner.weapons[0].icon == "/catalog/image/weapons/w-x"
        assert banner.weapons[0].rarity == 5
    finally:
        with get_connection() as conn:
            _restore_pickup(conn, saved)


def test_refresh_pickup_banners_prefers_resonator_image(monkeypatch):
    """A pickup character matched to a wuwa_resonator reuses the resonator head
    icon (and links its id) instead of the crawled Namuwiki banner avatar."""
    init_db()
    with get_connection() as conn:
        saved = _save_pickup(conn)

    try:
        monkeypatch.setattr(
            catalog, "_resonator_by_name",
            lambda: {catalog._norm_name("테스트캐릭"): {"id": 777, "image": "/catalog/image/characters/T_Test"}},
        )
        monkeypatch.setattr(catalog, "_weapon_by_name", lambda: {})

        def fake_all(page, kind):
            if kind == "character":
                return [{
                    "version": "9.9", "phase": 1, "banner_name": "b", "is_rerun": False,
                    "items": ["테스트캐릭"], "start_date": None, "end_date": None,
                    "icons": [{"alt": "명조 9.9 테스트캐릭", "src": "https://i/c.webp"}],
                }]
            return []

        monkeypatch.setattr(catalog, "_all_banner_history", fake_all)
        monkeypatch.setattr(catalog, "_collab_banner_history", lambda page, kind: [])
        # If the resonator match worked this must NOT be called; make it loud if it is.
        monkeypatch.setattr(
            catalog, "ensure_catalog_image",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("should use resonator image")),
        )

        assert catalog.refresh_pickup_banners() == 1
        banner = next(b for b in catalog.load_pickup_banners() if b.version == "9.9")
        assert banner.characters[0].avatar == "/catalog/image/characters/T_Test"
        assert banner.characters[0].catalog_id == 777
    finally:
        with get_connection() as conn:
            _restore_pickup(conn, saved)


def test_refresh_pickup_banners_collab_track_no_collision(monkeypatch):
    """A collab banner sharing a version+phase with a regular banner must not
    merge into the same slot -- it gets a distinct id and its own row."""
    init_db()
    with get_connection() as conn:
        saved = _save_pickup(conn)

    try:
        monkeypatch.setattr(
            catalog, "_all_banner_history",
            lambda page, kind: [{"version": "3.4", "phase": 1, "banner_name": "일반",
                                 "items": ["정규캐릭"] if kind == "character" else [], "icons": []}],
        )
        monkeypatch.setattr(
            catalog, "_collab_banner_history",
            lambda page, kind: [{"version": "3.4", "phase": 1, "banner_name": "콜라보",
                                 "items": ["콜라보캐릭"] if kind == "character" else [], "icons": []}],
        )
        monkeypatch.setattr(catalog, "_resonator_by_name", lambda: {})
        monkeypatch.setattr(catalog, "_weapon_by_name", lambda: {})
        monkeypatch.setattr(catalog, "ensure_catalog_image", lambda kind, iid, src: None)

        assert catalog.refresh_pickup_banners() == 2  # regular + collab, not merged
        v34 = [b for b in catalog.load_pickup_banners() if b.version == "3.4"]
        by_id = {b.id: b for b in v34}
        assert set(by_id) == {"3.4-p1", "3.4-collab-p1"}
        assert by_id["3.4-p1"].is_collab is False
        assert by_id["3.4-p1"].characters[0].name_ko == "정규캐릭"
        assert by_id["3.4-collab-p1"].is_collab is True
        assert by_id["3.4-collab-p1"].characters[0].name_ko == "콜라보캐릭"
    finally:
        with get_connection() as conn:
            _restore_pickup(conn, saved)
