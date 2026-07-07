import pytest

from src.wutheringgg import client


def test_find_data_chunk_picks_by_signature(monkeypatch):
    monkeypatch.setattr(client, "fetch_chunk_names", lambda: ["a.js", "b.js"])
    blobs = {
        "a.js": "unrelated code",
        "b.js": 'x=[{"Id":1603,"Name":"카멜리아","ResonantChainGroup":[]}]',
    }
    monkeypatch.setattr(client, "download_chunk", lambda n: blobs[n])
    text = client.find_data_chunk("characters")
    assert "카멜리아" in text


def test_find_data_chunk_raises_when_absent(monkeypatch):
    monkeypatch.setattr(client, "fetch_chunk_names", lambda: ["a.js"])
    monkeypatch.setattr(client, "download_chunk", lambda n: "nothing here")
    with pytest.raises(RuntimeError):
        client.find_data_chunk("characters")
