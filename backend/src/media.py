from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parents[1] / "media"
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB safety cap
_USER_AGENT = "WuWaHelper/1.0"

_ALLOWED_SCHEMES = ("http", "https")
_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # pragma: no cover - trivial
        return None


def _host_is_public(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


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


def download_image(source_url: str, dest_stem: Path) -> Path:
    """Download an image to dest_stem + a content-type-derived extension.

    Rejects non-http(s) schemes, private/loopback/metadata hosts, redirects,
    and non-image content types (SSRF hardening). Returns the written path.
    """
    parsed = urlparse(source_url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"disallowed url scheme: {parsed.scheme!r}")
    if not parsed.hostname or not _host_is_public(parsed.hostname):
        raise ValueError(f"disallowed url host: {parsed.hostname!r}")

    opener = build_opener(_NoRedirect)
    request = Request(source_url, headers={"User-Agent": _USER_AGENT})
    with opener.open(request, timeout=30) as response:
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        ext = _CONTENT_TYPE_EXT.get(content_type)
        if ext is None:
            raise ValueError(f"disallowed content-type: {content_type!r}")
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image exceeds {MAX_IMAGE_BYTES} bytes: {source_url}")

    dest = dest_stem.with_suffix(ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def ensure_hero_image(update_id: str, source_url: str | None) -> str | None:
    """Return the API-relative served path for the cached hero image, or None.

    Reuses an already-cached file (no re-download). A rejected or failed
    download yields None so the caller (refresh) can continue.
    """
    if cached_image_path(update_id) is not None:
        return f"/updates/image/{update_id}"
    if not source_url:
        return None
    try:
        download_image(source_url, updates_image_dir() / update_id)
    except Exception:
        return None
    return f"/updates/image/{update_id}"


# --- Catalog images (character avatars, weapon icons, echo icons) -----------
# Cached locally by (kind, id) and served from our own domain via
# GET /catalog/image/{kind}/{id}, mirroring the update-hero-image pattern.
CATALOG_KINDS = ("characters", "weapons", "echoes")


def catalog_image_dir(kind: str) -> Path:
    if kind not in CATALOG_KINDS:
        raise ValueError(f"unknown catalog image kind: {kind!r}")
    return media_dir() / kind


def cached_catalog_image_path(kind: str, item_id: str) -> Path | None:
    if kind not in CATALOG_KINDS:
        return None
    directory = media_dir() / kind
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{item_id}.*"))
    return matches[0] if matches else None


def ensure_catalog_image(kind: str, item_id: str, source_url: str | None) -> str | None:
    """Cache a catalog image locally; return its API-relative served path or None.

    Reuses an already-cached file (no re-download). A rejected/failed download
    yields None so the caller can continue.
    """
    if cached_catalog_image_path(kind, item_id) is not None:
        return f"/catalog/image/{kind}/{item_id}"
    if not source_url:
        return None
    try:
        download_image(source_url, catalog_image_dir(kind) / item_id)
    except Exception:
        return None
    return f"/catalog/image/{kind}/{item_id}"
