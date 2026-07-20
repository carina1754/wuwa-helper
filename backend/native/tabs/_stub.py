"""임시 스텁 탭 — 실제 구현 전 셸이 뜨도록. 채우면서 제거."""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from ..lang import LANG
from ..widgets import label, vbox


def make_stub(title_key: str) -> type[QWidget]:
    class _Stub(QWidget):
        def __init__(self) -> None:
            super().__init__()
            lay = vbox(self, margins=(24, 24, 24, 24))
            self._t = label("", "H1")
            self._m = label("준비 중…", "Muted")
            lay.addWidget(self._t)
            lay.addWidget(self._m)
            lay.addStretch(1)
            self.retranslate()

        def retranslate(self) -> None:
            self._t.setText(LANG.t(title_key))

    return _Stub
