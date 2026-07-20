"""명조 업데이트 탭(기본 탭) — 게임 패치 요약 카드 목록."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

from .. import engine, icons
from ..lang import LANG
from ..widgets import card, clear_layout, hbox, label, vbox


class _Hero(QWidget):
    """배너 이미지를 카드 배경으로 — cover 스케일(중앙 크롭) + 라운드 16 + 하단 어두운 그라데이션."""

    def __init__(self, pm: QPixmap) -> None:
        super().__init__()
        self._pm = pm
        self.setFixedHeight(240)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        p.setClipPath(path)
        # cover: 비율 유지로 위젯을 꽉 채운 뒤 넘치는 부분은 중앙 크롭
        spm = self._pm.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap((self.width() - spm.width()) // 2, (self.height() - spm.height()) // 2, spm)
        # 하단 어두운 그라데이션 — 오버레이 텍스트 가독성
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 190))
        p.fillRect(self.rect(), grad)
        p.end()


class _UpdateCard(QWidget):
    def __init__(self, update) -> None:
        super().__init__()
        self._u = update
        box = card()
        lay = vbox(box, margins=(20, 18, 20, 18), spacing=12)

        head = hbox(spacing=10)
        self._ver = QLabel(f"v{update.version}")
        self._ver.setObjectName("TagSrc")
        head.addWidget(self._ver)
        self._date = QLabel((update.release_date_kst or "")[:10])
        head.addWidget(self._date)
        head.addStretch(1)

        self._title = label("", None, wrap=True)

        pm = icons.update_pixmap(update.id)
        if not pm.isNull():
            # 웹판처럼 이미지 배경 + 텍스트 오버레이. 히어로 위 텍스트는 테마 무관 항상 흰색.
            hero = _Hero(pm)
            hlay = vbox(hero, margins=(20, 16, 20, 18), spacing=8)
            self._date.setStyleSheet("color:rgba(255,255,255,0.75);")
            hlay.addLayout(head)
            hlay.addStretch(1)
            self._title.setStyleSheet("color:#ffffff; font-size:21px; font-weight:800;")
            hlay.addWidget(self._title)
            lay.addWidget(hero)
        else:
            # 이미지 없으면 기존 텍스트 헤더 폴백
            self._date.setObjectName("Faint")
            lay.addLayout(head)
            self._title.setStyleSheet("font-size:20px; font-weight:800;")
            lay.addWidget(self._title)

        self._summary = label("", "Muted", wrap=True)
        lay.addWidget(self._summary)

        # 하이라이트 — 안쪽 톤 박스(Card2)에 불릿 목록
        self._hl_box = card("Card2")
        self._hl = vbox(self._hl_box, margins=(16, 12, 16, 12), spacing=6)
        lay.addWidget(self._hl_box)

        outer = vbox(self)
        outer.addWidget(box)
        self.retranslate()

    def retranslate(self) -> None:
        self._title.setText(LANG.field(self._u, "title"))
        self._summary.setText(LANG.field(self._u, "summary"))
        clear_layout(self._hl)
        items = LANG.list(self._u, "highlights")
        self._hl_box.setVisible(bool(items))
        for h in items:
            self._hl.addWidget(label(f"·  {h}", None, wrap=True))


class UpdatesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._cards: list[_UpdateCard] = []
        outer = vbox(self, margins=(0, 0, 0, 0))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self._lay = vbox(host, margins=(20, 20, 20, 20), spacing=14)
        for u in engine.game_updates():
            c = _UpdateCard(u)
            self._cards.append(c)
            self._lay.addWidget(c)
        self._lay.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll)

    def retranslate(self) -> None:
        for c in self._cards:
            c.retranslate()


if __name__ == "__main__":  # smoke: build + retranslate all langs headless
    import os
    import sys
    import tempfile

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp())
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")

    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    tab = UpdatesTab()
    assert tab._cards, "updates empty"
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        tab.retranslate()
    LANG.set("ko")
    print("updates ok")
