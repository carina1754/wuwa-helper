from fastapi.testclient import TestClient

from main import app
from src.database import get_connection
from src.models import AnalysisSession, VisionExtractionResult

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_sync_user_rejects_missing_or_wrong_secret(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", "correct-secret")
    payload = {"email": "no-secret@example.com", "role": "user"}

    response = client.post("/auth/sync-user", json=payload)
    assert response.status_code == 401

    response = client.post("/auth/sync-user", json=payload, headers={"X-Internal-Secret": "wrong-secret"})
    assert response.status_code == 401


def test_sync_user_accepts_matching_secret(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_SECRET", "correct-secret")
    email = "sync-user-test@example.com"
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()

    response = client.post(
        "/auth/sync-user",
        json={"email": email, "name": "Test User", "role": "user"},
        headers={"X-Internal-Secret": "correct-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email

    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()


def test_sync_user_rejects_when_secret_not_configured(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_SECRET", raising=False)
    response = client.post(
        "/auth/sync-user",
        json={"email": "no-secret@example.com", "role": "user"},
        headers={"X-Internal-Secret": "anything"},
    )
    assert response.status_code == 401


def test_rules_endpoint_returns_seed_rules():
    response = client.get("/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(rule["character_name"] == "default_main_dps" for rule in data)
    assert any(rule["character_name"] == "Changli" for rule in data)


def test_pickup_schedule_endpoint_returns_korean_schedule():
    response = client.get("/pickup-schedule?year=2026")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["month"] == 1 and item["label_ko"] == "첫 픽업" for item in data)
    assert all("label_ko" in item for item in data)


def test_updates_endpoint_returns_korean_summaries():
    response = client.get("/updates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["version"] == "3.5" for item in data)
    assert all("summary_ko" in item for item in data)


def test_site_updates_endpoint_returns_service_notices():
    response = client.get("/site-updates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == "service-prep-2026-07-06" for item in data)
    infra_terms = ("Caddy", "127.0.0.1", "리버스 프록시", ":3000", ":8000")
    assert not any(term in item["description_ko"] for item in data for term in infra_terms)


def test_history_round_trip():
    with get_connection() as conn:
        conn.execute("DELETE FROM analysis_sessions WHERE id = %s", ("test-session",))
        conn.commit()
    session = AnalysisSession(
        id="test-session",
        created_at="2026-07-05T00:00:00Z",
        image_filename=None,
        extraction=VisionExtractionResult(),
        diagnoses=[],
        report="test report",
        metadata={"source": "test"},
    )
    save_response = client.post("/history", json=session.model_dump())
    assert save_response.status_code == 200
    assert save_response.json()["id"] == "test-session"

    list_response = client.get("/history")
    assert list_response.status_code == 200
    assert any(item["id"] == "test-session" for item in list_response.json())

    detail_response = client.get("/history/test-session")
    assert detail_response.status_code == 200
    assert detail_response.json()["report"] == "test report"
    with get_connection() as conn:
        conn.execute("DELETE FROM analysis_sessions WHERE id = %s", ("test-session",))
        conn.commit()


def test_vision_extract_uses_mock_without_llm(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    response = client.post(
        "/vision/extract",
        files={"file": ("sample.png", b"not-a-real-image", "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["screen_type"] in ["character_status", "echo_detail", "weapon_detail", "inventory", "team", "unknown"]
    assert len(data["snapshot"]["echoes"]) == 5
    assert any("mock" in warning.lower() for warning in data["warnings"])


def test_analyze_character_returns_diagnoses_and_report(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    extraction = client.post(
        "/vision/extract",
        files={"file": ("sample.png", b"sample", "image/png")},
    ).json()
    response = client.post(
        "/analyze/character",
        json={"snapshot": extraction["snapshot"], "fallback_role": "main_dps"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["diagnoses"]
    assert "바로 할 일" in data["report"] or "Next actions" in data["report"]


def test_update_image_route_serves_cached_file(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    updates_dir = tmp_path / "updates"
    updates_dir.mkdir(parents=True)
    (updates_dir / "wuwa-3-4.jpg").write_bytes(b"img-bytes")

    response = client.get("/updates/image/wuwa-3-4")
    assert response.status_code == 200
    assert response.content == b"img-bytes"


def test_update_image_route_404_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    response = client.get("/updates/image/does-not-exist")
    assert response.status_code == 404


def test_ai_chat_returns_mock_without_llm(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    response = client.post(
        "/ai/chat",
        json={
            "messages": [{"role": "user", "content": "딜러 추천해줘"}],
            "profile": {"union_level": 40},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_final"] is False
    assert data["recommendation"] is None
    assert isinstance(data["reply"], str) and data["reply"]


def test_ai_recommendation_round_trip():
    payload = {
        "user_id": None,
        "profile": {"union_level": 45},
        "conversation": [{"role": "user", "content": "저장 테스트"}],
        "recommendation": {
            "summary": "테스트 빌드",
            "team": [{"resonator_id": "1402", "role": "support"}],
            "upgrade_order": ["무기 강화"],
        },
        "title": "저장 테스트 빌드",
    }
    save = client.post("/ai/recommendations", json=payload)
    assert save.status_code == 200
    rec_id = save.json()["id"]
    assert rec_id
    try:
        listing = client.get("/ai/recommendations")
        assert listing.status_code == 200
        assert any(item["id"] == rec_id for item in listing.json())

        detail = client.get(f"/ai/recommendations/{rec_id}")
        assert detail.status_code == 200
        assert detail.json()["title"] == "저장 테스트 빌드"
        assert detail.json()["recommendation"]["team"][0]["resonator_id"] == "1402"
    finally:
        with get_connection() as conn:
            conn.execute("DELETE FROM ai_recommendations WHERE id = %s", (rec_id,))
            conn.commit()


def test_ai_recommendation_detail_404_when_missing():
    response = client.get("/ai/recommendations/does-not-exist")
    assert response.status_code == 404


def test_update_image_route_rejects_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    # Starlette's router decodes/normalizes "..%2F.." style segments before
    # they reach the handler, so that no longer exercises the guard. Use an
    # id that reaches the handler but fails the `[A-Za-z0-9_-]+` regex guard
    # in main.py directly (the "." is disallowed).
    response = client.get("/updates/image/bad.name")
    assert response.status_code == 404
