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
