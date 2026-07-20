"""공용 위젯 — 텍스트는 전부 인자로 받음(여기서 i18n import 안 함).

카드/구분선/칩/섹션제목/레어리티 아이콘/그리드셀/라벨슬라이더.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .theme import rarity_color


# --- primitives --------------------------------------------------------------
def card(obj: str = "Card") -> QFrame:
    f = QFrame()
    f.setObjectName(obj)
    return f


def hsep() -> QFrame:
    f = QFrame()
    f.setObjectName("Sep")
    f.setFixedHeight(1)
    return f


def label(text: str, obj: str | None = None, wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if obj:
        lb.setObjectName(obj)
    if wrap:
        lb.setWordWrap(True)
    return lb


def chip(text: str, checkable: bool = True) -> QPushButton:
    b = QPushButton(text)
    b.setObjectName("Chip")
    b.setCheckable(checkable)
    b.setCursor(Qt.PointingHandCursor)
    return b


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def vbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing=8) -> QVBoxLayout:
    lay = QVBoxLayout(parent)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


def hbox(parent: QWidget | None = None, margins=(0, 0, 0, 0), spacing=8) -> QHBoxLayout:
    lay = QHBoxLayout(parent)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return lay


# --- rarity icon tile --------------------------------------------------------
class IconTile(QLabel):
    """카탈로그 아이콘 + 레어리티 색 테두리."""

    def __init__(self, kind: str, item_id, rarity: int | None, size: int = 72) -> None:
        super().__init__()
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(True)
        color = rarity_color(rarity)
        self.setStyleSheet(
            f"border:2px solid {color}; border-radius:12px; background:rgba(120,120,130,0.12);"
        )
        pm = icons.catalog_pixmap(kind, item_id, size * 2)
        if not pm.isNull():
            self.setPixmap(pm)


class GridCell(QFrame):
    """클릭 가능한 카탈로그 셀(아이콘 + 이름). clicked 시그널로 id 전달."""

    clicked = Signal(object)

    def __init__(self, kind: str, item_id, rarity: int | None, name: str, size: int = 72) -> None:
        super().__init__()
        self._id = item_id
        self.setObjectName("Cell")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(size + 36)  # FlowLayout 반응형 그리드용 균일 폭
        lay = vbox(self, margins=(8, 10, 8, 8), spacing=6)
        lay.setAlignment(Qt.AlignHCenter)
        tile = IconTile(kind, item_id, rarity, size)
        lay.addWidget(tile, 0, Qt.AlignHCenter)
        cap = QLabel(name)
        cap.setAlignment(Qt.AlignHCenter)
        cap.setWordWrap(True)
        cap.setStyleSheet("font-size:12px;")
        lay.addWidget(cap)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._id)
        super().mousePressEvent(event)


class FlowLayout(QLayout):
    """가로 공간에 맞춰 줄바꿈하는 레이아웃(반응형 그리드) — Qt 공식 예제 포팅."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 10) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self._gap = spacing
        self._items = []

    def addItem(self, item) -> None:  # noqa: N802 (Qt signature)
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i: int):  # noqa: N802
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i: int):  # noqa: N802
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for it in self._items:
            size = size.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x, y, line_h = rect.x(), rect.y(), 0
        for it in self._items:
            hint = it.sizeHint()
            nx = x + hint.width() + self._gap
            if nx - self._gap > rect.right() + 1 and line_h > 0:
                x = rect.x()
                y += line_h + self._gap
                nx = x + hint.width() + self._gap
                line_h = 0
            if not test_only:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x = nx
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y()


def flow_of(cells: list[QWidget], spacing: int = 10) -> QWidget:
    host = QWidget()
    lay = FlowLayout(host, spacing=spacing)
    for w in cells:
        lay.addWidget(w)
    return host


def rounded_pixmap(pm: QPixmap, radius: int) -> QPixmap:
    """모서리 라운드 처리된 픽스맵(배너 이미지용)."""
    out = QPixmap(pm.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, pm.width(), pm.height(), radius, radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


# --- labeled slider ----------------------------------------------------------
class LabeledSlider(QWidget):
    """라벨 + 슬라이더 + 현재값. valueChanged(int)."""

    valueChanged = Signal(int)

    def __init__(
        self,
        text: str,
        minimum: int,
        maximum: int,
        value: int,
        suffix: str = "",
        fmt: Callable[[int], str] | None = None,
    ) -> None:
        super().__init__()
        self._suffix = suffix
        self._fmt = fmt
        lay = hbox(self, spacing=10)
        self._name = QLabel(text)
        self._name.setMinimumWidth(84)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(value)
        self._slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._val = QLabel()
        self._val.setObjectName("Accent")
        self._val.setMinimumWidth(48)
        self._val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self._name)
        lay.addWidget(self._slider, 1)
        lay.addWidget(self._val)
        self._slider.valueChanged.connect(self._on_change)
        self._render(value)

    def _render(self, v: int) -> None:
        self._val.setText(self._fmt(v) if self._fmt else f"{v}{self._suffix}")

    def _on_change(self, v: int) -> None:
        self._render(v)
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, v: int) -> None:  # noqa: N802 (Qt convention)
        self._slider.setValue(v)


if __name__ == "__main__":  # smoke: build widgets headless, no crash
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    w = QWidget()
    lay = vbox(w, margins=(12, 12, 12, 12))
    lay.addWidget(label("hello", "H1"))
    lay.addWidget(hsep())
    lay.addWidget(chip("filter"))
    lay.addWidget(GridCell("characters", 1, 5, "테스트"))
    ls = LabeledSlider("레벨", 1, 90, 90)
    lay.addWidget(ls)
    assert ls.value() == 90
    w.show()
    print("widgets ok")
