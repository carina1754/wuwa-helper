from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB safety cap
_USER_AGENT = "WuWaHelper/1.0"
_KNOWN_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def media_dir() -> Path:
    override = os.getenv("MEDIA_DIR")
    return Path(override) if override else DEFAULT_MEDIA_DIR


def updates_image_dir() -> Path:
    return media_dir() / "updates"


def cached_image_path(update_id: str) -> Path | None:
    directory = updates_image_dir()
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{update_id}.*"))
    return matches[0] if matches else None


def _extension_for(source_url: str) -> str:
    lowered = source_url.lower().split("?", 1)[0]
    for ext in _KNOWN_EXTS:
        if lowered.endswith(ext):
            return ext
    return ".jpg"


def download_image(source_url: str, dest: Path) -> None:
    request = Request(source_url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=30) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image exceeds {MAX_IMAGE_BYTES} bytes: {source_url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def ensure_hero_image(update_id: str, source_url: str | None) -> str | None:
    """Return the API-relative served path for the cached hero image, or None.

    Reuses an already-cached file (no re-download). A failed download yields
    None so the caller (refresh) can continue rather than aborting.
    """
    if cached_image_path(update_id) is not None:
        return f"/updates/image/{update_id}"
    if not source_url:
        return None
    dest = updates_image_dir() / f"{update_id}{_extension_for(source_url)}"
    try:
        download_image(source_url, dest)
    except Exception:
        return None
    return f"/updates/image/{update_id}"
