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


def test_characters_endpoint_returns_catalog():
    response = client.get("/characters")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 50
    assert any(character["name"] == "Changli" for character in data)
    assert all("default_sonata" in character for character in data)


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
    assert any("Caddy" in item["description_ko"] for item in data)


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


def test_vision_extract_uses_mock_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
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
