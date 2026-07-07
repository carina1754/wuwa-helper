"""Cache wuthering.gg image assets locally via the existing media infra."""
from __future__ import annotations

import os

from src.media import ensure_catalog_image
from src.wutheringgg.normalize import image_url


def cache_asset(kind: str, category: str, asset: str | None) -> str | None:
    """Cache one asset and return its API-relative served path (or None).

    ``item_id`` is the asset filename without extension, mirroring how
    ``ensure_catalog_image`` keys and serves catalog images.
    """
    if not asset:
        return None
    item_id = os.path.splitext(asset)[0]
    return ensure_catalog_image(kind, item_id, image_url(category, asset))
