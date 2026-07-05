from fastapi.testclient import TestClient

from main import app
from src.models import AnalysisSession, VisionExtractionResult

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_rules_endpoint_returns_seed_rules():
    response = client.get("/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(rule["character_name"] == "default_main_dps" for rule in data)


def test_history_round_trip():
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
