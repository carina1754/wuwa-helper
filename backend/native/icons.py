"""카탈로그 아이콘 → QPixmap (HTTP 대신 실제 파일에서 직접 로드).

kind: "characters"(공명자) | "weapons"(무기) | "echoes"(에코).
item_id 는 카탈로그 정수 id 를 문자열로. 없으면 빈 QPixmap.
QPixmapCache 로 중복 디코드 방지(265 에코 등).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPixmapCache

from src.media import cached_catalog_image_path, cached_image_path


def catalog_pixmap(kind: str, item_id, size: int | None = None) -> QPixmap:
    key = f"cat:{kind}:{item_id}:{size or 0}"
    cached = QPixmapCache.find(key)
    if cached is not None:
        return cached
    path = cached_catalog_image_path(kind, str(item_id))
    pm = QPixmap(str(path)) if path else QPixmap()
    if size and not pm.isNull():
        pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    QPixmapCache.insert(key, pm)
    return pm


def update_pixmap(update_id: str) -> QPixmap:
    path = cached_image_path(update_id)
    return QPixmap(str(path)) if path else QPixmap()
