from __future__ import annotations

import json

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
    # load_sonata_sets() now serves the file-primary catalog (data/catalog), so
    # verify the (dormant Namuwiki) writer landed the row via a direct table read.
    with get_connection() as conn:
        row = conn.execute("SELECT data_json FROM sonata_set WHERE id = %s", (sid,)).fetchone()
    assert row is not None
    stored = json.loads(row["data_json"])
    assert stored["id"] == sid
    assert stored["icon"] == f"/catalog/image/echoes/{sid}"

    with get_connection() as conn:
        conn.execute("DELETE FROM sonata_set WHERE id = %s", (sid,))
        conn.commit()


def test_data_endpoints_return_lists():
    assert isinstance(client.get("/sonata-sets").json(), list)
    assert isinstance(client.get("/pickup-banners").json(), list)


# refresh_pickup_banners() 테스트는 제거됨: 크롤러→DB 갱신은 스탠드얼론에서 휴면
# (런타임 호출 0). load_pickup_banners() 는 파일(data/content)에서 읽으므로 DB
# 쓰기 경로와 분리되어 검증 대상이 아니다. 라이브 읽기 경로는 위 엔드포인트 테스트가 커버.
