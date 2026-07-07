from __future__ import annotations

from src import media


def test_media_dir_honors_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert media.media_dir() == tmp_path


def test_ensure_hero_image_none_without_source_or_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert media.ensure_hero_image("wuwa-9-9", None) is None


def test_ensure_hero_image_downloads_and_returns_served_path(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    def fake_download(url, dest_stem):
        dest = dest_stem.with_suffix(".jpg")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake-image-bytes")
        return dest

    monkeypatch.setattr(media, "download_image", fake_download)
    result = media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg")
    assert result == "/updates/image/wuwa-3-4"
    cached = media.cached_image_path("wuwa-3-4")
    assert cached is not None
    assert cached.name.startswith("wuwa-3-4.")
    assert cached.read_bytes() == b"fake-image-bytes"


def test_ensure_hero_image_skips_download_when_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    cached = tmp_path / "updates" / "wuwa-3-4.png"
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b"already-here")

    def boom(url, dest_stem):
        raise AssertionError("must not download when a cached file exists")

    monkeypatch.setattr(media, "download_image", boom)
    assert media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg") == "/updates/image/wuwa-3-4"


def test_ensure_hero_image_returns_none_on_download_failure(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))

    def boom(url, dest_stem):
        raise OSError("network down")

    monkeypatch.setattr(media, "download_image", boom)
    assert media.ensure_hero_image("wuwa-3-4", "https://cdn.example/x.jpg") is None


def test_download_image_rejects_ssrf_urls(tmp_path):
    try:
        media.download_image("file:///etc/hostname", tmp_path / "x")
        raised = False
    except ValueError:
        raised = True
    assert raised

    try:
        media.download_image("http://127.0.0.1/a.jpg", tmp_path / "x")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_ensure_hero_image_rejects_ssrf_url_and_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    assert media.ensure_hero_image("wuwa-x", "file:///etc/passwd") is None
    assert media.cached_image_path("wuwa-x") is None
