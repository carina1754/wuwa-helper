"""다크/라이트 테마 — 토스(TDS) 스타일 디자인 시스템.

그레이 배경 + 보더리스 화이트 카드, 토스블루 액센트, 틴트 배지, 굵은 타이포.
ThemeState 싱글턴이 토글/저장/시그널.
"""
from __future__ import annotations

import os
import tempfile
from string import Template

from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF

from . import settings

# 토스 어댑티브 그레이 + 토스블루. surface=카드, surface2=인풋/칩 필, surface3=호버 단계.
DARK = {
    "bg": "#101013", "surface": "#17171c", "surface2": "#26262c", "surface3": "#2e2e36",
    "line": "rgba(255,255,255,0.06)", "line2": "rgba(255,255,255,0.10)",
    "fg": "#e5e8eb", "fg_soft": "#b0b8c1", "muted": "#8b95a1", "faint": "#6b7684",
    "accent": "#4890fe", "accent_hover": "#3a7de8", "accent_ink": "#ffffff",
    "gold": "#ffa14e", "gold_soft": "rgba(255,161,78,0.14)",
    "sel": "rgba(72,144,254,0.16)",
}
LIGHT = {
    "bg": "#f2f4f6", "surface": "#ffffff", "surface2": "#f2f4f6", "surface3": "#e5e8eb",
    "line": "rgba(0,23,51,0.06)", "line2": "rgba(0,23,51,0.12)",
    "fg": "#191f28", "fg_soft": "#333d4b", "muted": "#6b7684", "faint": "#8b95a1",
    "accent": "#3182f6", "accent_hover": "#1b64da", "accent_ink": "#ffffff",
    "gold": "#e8640a", "gold_soft": "rgba(232,100,10,0.10)",
    "sel": "rgba(49,130,246,0.10)",
}

# 5★ 골드 / 4★ 바이올렛 / 그 외 중립 (레어리티 링 — 게임 시맨틱, 테마 무관)
RARITY_RING = {5: "#c9a86a", 4: "#9b7bd4"}


def rarity_color(rarity: int | None) -> str:
    return RARITY_RING.get(int(rarity) if rarity else 0, "rgba(140,140,150,0.5)")


_QSS = Template("""
/* base — transparent so container widgets don't paint over cards; only window/dialog fill bg */
QWidget { background: transparent; color: $fg; font-family: 'Pretendard','Pretendard Variable','Malgun Gothic','Segoe UI',sans-serif; font-size: 14px; }
QMainWindow, QDialog { background: $bg; }
QToolTip { background: $surface2; color: $fg; border: 1px solid $line2; padding: 6px 10px; border-radius: 6px; font-size: 12px; }
QMenu { background: $surface; border: 1px solid $line; border-radius: 14px; padding: 6px; }
QMenu::item { padding: 8px 14px; border-radius: 8px; }
QMenu::item:selected { background: $surface2; color: $fg; }

/* scrollbars — slim, subtle, no arrows */
QScrollArea, QAbstractScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px 1px; }
QScrollBar::handle:vertical { background: $line2; border-radius: 4px; min-height: 34px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 1px 2px; }
QScrollBar::handle:horizontal { background: $line2; border-radius: 4px; min-width: 34px; }
QScrollBar::handle:horizontal:hover { background: $muted; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; background: transparent; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* typography — 토스 헤드라인: 크고 굵게, 보조 텍스트는 그레이 스케일 */
QLabel#Brand { font-size: 19px; font-weight: 800; }
QLabel#Kicker { color: $faint; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#H1 { font-size: 24px; font-weight: 800; }
QLabel#H2 { font-size: 17px; font-weight: 700; }
QLabel#Muted { color: $muted; }
QLabel#Faint { color: $faint; font-size: 12px; }
QLabel#Accent { color: $accent; font-weight: 700; }
QLabel#Gold { color: $gold; font-weight: 800; }

/* header icon buttons — borderless, soft hover */
QPushButton#IconBtn { border: none; border-radius: 12px; min-width: 38px; max-width: 38px; min-height: 38px; max-height: 38px; color: $muted; background: transparent; }
QPushButton#IconBtn:hover { background: $line; color: $fg; }
QPushButton#IconBtn:checked { background: $sel; color: $accent; }

/* tab bar — 토스 내비: 볼드 텍스트, 비활성 그레이/활성 진한색, 밑줄·박스 없음 */
QTabWidget::pane { border: none; background: transparent; }
QTabWidget::tab-bar { left: 14px; }
QTabBar { qproperty-drawBase: 0; background: transparent; }
QTabBar::tab { background: transparent; color: $faint; padding: 10px 14px; margin-right: 2px; border: none; font-size: 15px; font-weight: 700; }
QTabBar::tab:hover { color: $fg_soft; }
QTabBar::tab:selected { color: $fg; }

/* cards — 보더리스, 배경 대비로 뜨는 토스 카드 */
QFrame#Card { background: $surface; border: none; border-radius: 20px; }
QFrame#Card2 { background: $surface2; border: none; border-radius: 16px; }
QFrame#Cell { background: $surface; border: none; border-radius: 16px; }
QFrame#Cell:hover { background: $surface2; }
QFrame#Sep { background: $line; max-height: 1px; min-height: 1px; border: none; }

/* buttons — primary 파랑 필, 기본은 그레이 필(tertiary) */
QPushButton { background: $surface2; color: $fg; border: none; border-radius: 12px; padding: 9px 16px; font-weight: 600; }
QPushButton:hover { background: $surface3; }
QPushButton:disabled { color: $faint; background: $surface2; }
QPushButton#Accent { background: $accent; color: $accent_ink; border: none; font-weight: 700; padding: 10px 18px; }
QPushButton#Accent:hover { background: $accent_hover; }
QPushButton#Accent:disabled { background: $surface2; color: $faint; }
QPushButton#Ghost { background: transparent; color: $fg_soft; border: 1px solid $line2; }
QPushButton#Ghost:hover { background: $surface2; }
QPushButton#Ghost:checked { background: $sel; color: $accent; border: 1px solid transparent; font-weight: 700; }
QPushButton#Chip { background: $surface2; color: $muted; border: 1px solid transparent; border-radius: 16px; padding: 6px 14px; font-size: 13px; font-weight: 600; }
QPushButton#Chip:hover { background: $surface3; color: $fg; }
QPushButton#Chip:checked { background: $sel; color: $accent; border: 1px solid transparent; font-weight: 700; }
QPushButton#Link { background: transparent; border: none; color: $accent; padding: 0; text-align: left; font-weight: 600; }

/* text inputs — 토스 필드: 필 배경 + 포커스 파랑 아웃라인 */
QLineEdit, QTextEdit, QPlainTextEdit { background: $surface2; border: 1px solid transparent; border-radius: 12px; padding: 9px 13px; color: $fg; selection-background-color: $sel; selection-color: $fg; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid $accent; }

/* combo box + popup + asset-free triangle arrow */
QComboBox { background: $surface2; border: 1px solid transparent; border-radius: 12px; padding: 8px 13px; padding-right: 27px; color: $fg; min-height: 20px; font-weight: 600; }
QComboBox:hover { background: $surface3; }
QComboBox:focus { border: 1px solid $accent; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right; width: 24px; border: none; background: transparent; }
QComboBox::down-arrow { image: url("$arrow_down"); width: 11px; height: 11px; margin-right: 9px; }
QComboBox QAbstractItemView { background: $surface; border: 1px solid $line; border-radius: 12px; padding: 5px; selection-background-color: $sel; selection-color: $fg; outline: none; }
QComboBox QAbstractItemView::item { padding: 7px 11px; border-radius: 8px; min-height: 22px; }

/* spinbox — 필 배경 + 플랫 버튼 + asset-free triangle arrows */
QSpinBox, QDoubleSpinBox { background: $surface2; border: 1px solid transparent; border-radius: 12px; padding: 7px 11px; padding-right: 23px; color: $fg; min-height: 20px; font-weight: 600; }
QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid $accent; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 21px; border: none; border-top-right-radius: 12px; background: transparent; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 21px; border: none; border-bottom-right-radius: 12px; background: transparent; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: $surface3; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("$arrow_up"); width: 9px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("$arrow_down"); width: 9px; height: 9px; }

/* sliders — 파랑 채움 + 화이트 핸들 */
QSlider::groove:horizontal { height: 5px; background: $surface3; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { background: #ffffff; border: 1px solid rgba(2,13,30,0.14); width: 17px; height: 17px; margin: -7px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { border-color: $accent; }

/* checkbox — 파랑 필 + 화이트 체크 */
QCheckBox { spacing: 8px; color: $fg; }
QCheckBox::indicator { width: 19px; height: 19px; border: 1px solid $line2; border-radius: 6px; background: $surface2; }
QCheckBox::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; image: url("$check"); }

/* tags — 틴트 배지(보더리스) */
QLabel#Tag { background: $surface2; border: none; border-radius: 8px; padding: 4px 10px; color: $muted; font-size: 12px; font-weight: 600; }
QLabel#TagSrc { background: $sel; color: $accent; border: none; border-radius: 8px; padding: 4px 10px; font-size: 12px; font-weight: 600; }

/* 섹션 상태 도트(진행중/예정/종료) — QSS 라 테마 토글 시 자동 갱신 */
QLabel#DotLive, QLabel#DotSoon, QLabel#DotEnded { min-width: 8px; max-width: 8px; min-height: 8px; max-height: 8px; border-radius: 4px; }
QLabel#DotLive { background: $accent; }
QLabel#DotSoon { background: $gold; }
QLabel#DotEnded { background: $muted; }

/* table rows (픽업 일정 등) + status/type pills — 토스 배지: 틴트 배경 + 유색 텍스트 */
QFrame#Row:hover { background: $surface2; border-radius: 12px; }
QLabel#PillLive { background: $sel; color: $accent; border-radius: 11px; padding: 4px 12px; font-size: 12px; font-weight: 700; }
QLabel#PillSoon { background: $gold_soft; color: $gold; border-radius: 11px; padding: 4px 12px; font-size: 12px; font-weight: 700; }
QLabel#PillEnded { background: $surface2; color: $muted; border-radius: 11px; padding: 4px 12px; font-size: 12px; font-weight: 600; }
QLabel#PillNew { background: $gold_soft; color: $gold; border: none; border-radius: 10px; padding: 4px 11px; font-size: 12px; font-weight: 700; }
QLabel#PillRerun { background: $surface2; color: $muted; border: none; border-radius: 10px; padding: 4px 11px; font-size: 12px; font-weight: 600; }
""")


# Qt QSS 는 sub-control 화살표에 CSS 삼각형 트릭이 불안정 → QPainter 로 작은 PNG 를
# 런타임 생성해 image:url() 로 참조(에셋 파일 불필요). 색·방향별 캐시.
_GLYPH_CACHE: dict[str, str] = {}
_GLYPH_DIR = os.path.join(tempfile.gettempdir(), "wuwa_ui_glyphs")


def _glyph_png(kind: str, color: str) -> str:
    """kind: 'down'|'up'|'check'. 지정 색의 12/22px 안티에일리어스 글리프 PNG 경로(QSS url용, 슬래시). 앱 없으면 ''."""
    key = f"{kind}_{color.lstrip('#')}"
    if key in _GLYPH_CACHE:
        return _GLYPH_CACHE[key]
    try:
        from PySide6.QtWidgets import QApplication
        if QApplication.instance() is None:  # QPixmap 은 QGuiApplication 필요
            return ""
        n = 22
        pm = QPixmap(n, n)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = QColor(color)
        cx = cy = n / 2
        if kind == "check":
            pen = QPen(c)
            pen.setWidthF(2.6)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPolyline(QPolygonF([QPointF(5, 11.5), QPointF(9.5, 16), QPointF(16.5, 7)]))
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            w, h = 11.0, 6.5
            if kind == "up":
                pts = [QPointF(cx - w / 2, cy + h / 2), QPointF(cx + w / 2, cy + h / 2), QPointF(cx, cy - h / 2)]
            else:  # down
                pts = [QPointF(cx - w / 2, cy - h / 2), QPointF(cx + w / 2, cy - h / 2), QPointF(cx, cy + h / 2)]
            p.drawPolygon(QPolygonF(pts))
        p.end()
        os.makedirs(_GLYPH_DIR, exist_ok=True)
        path = os.path.join(_GLYPH_DIR, f"{key}.png")
        pm.save(path, "PNG")
        url = path.replace("\\", "/")
        _GLYPH_CACHE[key] = url
        return url
    except Exception:  # noqa: BLE001 — 글리프 실패해도 UI 는 떠야 함
        return ""


def build_qss(palette: dict) -> str:
    tokens = dict(palette)
    tokens["arrow_down"] = _glyph_png("down", palette["muted"])
    tokens["arrow_up"] = _glyph_png("up", palette["muted"])
    tokens["check"] = _glyph_png("check", palette["accent_ink"])
    return _QSS.substitute(tokens)


class ThemeState(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        # settings 에 theme 키가 없으면 dark 기본
        self._dark = settings.load().get("theme", "dark") != "light"

    @property
    def dark(self) -> bool:
        return self._dark

    @property
    def palette(self) -> dict:
        return DARK if self._dark else LIGHT

    def qss(self) -> str:
        return build_qss(self.palette)

    def toggle(self) -> None:
        self._dark = not self._dark
        settings.save(theme="dark" if self._dark else "light")
        self.changed.emit()


THEME = ThemeState()
