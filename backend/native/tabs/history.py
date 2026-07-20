"""기록 탭 — 저장된 AI 빌드 추천 목록 + 상세 + 삭제."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QMessageBox,
    QScrollArea,
    QWidget,
)

from .. import engine
from ..lang import LANG
from ..widgets import card, hbox, hsep, label, vbox

STR = {
    "ko": {
        "title": "기록", "empty": "저장된 추천이 없습니다.",
        "delete": "삭제", "team": "추천 팀", "upgrade": "성장 우선순위",
        "confirm": "이 추천을 삭제할까요?", "pick": "선택하세요",
        "main_dps": "메인 딜러", "sub_dps": "서브 딜러", "support": "서포터", "healer": "힐러",
    },
    "en": {
        "title": "History", "empty": "No saved recommendations.",
        "delete": "Delete", "team": "Recommended team", "upgrade": "Upgrade priority",
        "confirm": "Delete this recommendation?", "pick": "Select one",
        "main_dps": "Main DPS", "sub_dps": "Sub DPS", "support": "Support", "healer": "Healer",
    },
    "ja": {
        "title": "履歴", "empty": "保存された提案がありません。",
        "delete": "削除", "team": "おすすめ編成", "upgrade": "育成の優先度",
        "confirm": "この提案を削除しますか？", "pick": "選択してください",
        "main_dps": "メインアタッカー", "sub_dps": "サブアタッカー", "support": "サポーター", "healer": "ヒーラー",
    },
    "zhHans": {
        "title": "记录", "empty": "没有已保存的推荐。",
        "delete": "删除", "team": "推荐队伍", "upgrade": "培养优先级",
        "confirm": "要删除这条推荐吗？", "pick": "请选择",
        "main_dps": "主C", "sub_dps": "副C", "support": "辅助", "healer": "治疗",
    },
}


class _RecordCard(QFrame):
    """클릭 가능한 기록 카드(제목 + 날짜). clicked 로 id 전달."""

    clicked = Signal(str)

    def __init__(self, rec) -> None:
        super().__init__()
        self._id = rec.id
        self.setObjectName("Cell")
        self.setCursor(Qt.PointingHandCursor)
        lay = vbox(self, margins=(12, 10, 12, 10), spacing=3)
        lay.addWidget(label(rec.title or rec.id, "H2", wrap=True))
        lay.addWidget(label((rec.created_at or "")[:10], "Faint"))

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt signature)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._id)
        super().mousePressEvent(event)


class HistoryTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._reso = {str(r["id"]): r for r in engine.resonators()}
        self._weap = {str(w["id"]): w for w in engine.weapons()}
        self._selected: str | None = None

        root = hbox(self, margins=(20, 20, 20, 20), spacing=16)

        # 왼쪽: 목록
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(300)
        left_host = QWidget()
        self._list = vbox(left_host, spacing=8)
        self._title = label("", "H1")
        self._list.addWidget(self._title)
        self._empty = label("", "Muted", wrap=True)
        self._list.addWidget(self._empty)
        self._list.addStretch(1)
        left_scroll.setWidget(left_host)
        root.addWidget(left_scroll)

        # 오른쪽: 상세
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        detail_host = QWidget()
        self._detail = vbox(detail_host, spacing=10)
        self._detail.addStretch(1)
        right_scroll.setWidget(detail_host)
        root.addWidget(right_scroll, 1)

        self._cards: list[_RecordCard] = []
        self.refresh()
        self.retranslate()

    # --- 목록 --------------------------------------------------------------
    def refresh(self) -> None:
        for c in self._cards:
            c.deleteLater()
        self._cards.clear()
        records = engine.ai_list()
        self._empty.setVisible(not records)
        insert_at = self._list.count() - 1  # stretch 앞
        for rec in records:
            c = _RecordCard(rec)
            c.clicked.connect(self._select)
            self._cards.append(c)
            self._list.insertWidget(insert_at, c)
            insert_at += 1
        if self._selected and not any(c._id == self._selected for c in self._cards):
            self._clear_detail()

    def _select(self, rec_id: str) -> None:
        self._selected = rec_id
        rec = engine.ai_get(rec_id)
        self._render_detail(rec)

    # --- 상세 --------------------------------------------------------------
    def _clear_detail(self) -> None:
        self._selected = None
        from ..widgets import clear_layout

        clear_layout(self._detail)
        self._detail.addWidget(label(LANG.m(STR, "pick"), "Muted"))
        self._detail.addStretch(1)

    def _render_detail(self, rec) -> None:
        from ..widgets import clear_layout

        clear_layout(self._detail)
        if rec is None:
            self._clear_detail()
            return

        header = hbox(spacing=8)
        header.addWidget(label(rec.title or rec.id, "H1", wrap=True), 1)
        del_btn = _delete_button(LANG.m(STR, "delete"))
        del_btn.clicked.connect(lambda: self._confirm_delete(rec.id))
        header.addWidget(del_btn)
        self._detail.addLayout(header)
        self._detail.addWidget(label((rec.created_at or "")[:10], "Faint"))
        self._detail.addWidget(hsep())

        recc = rec.recommendation
        if recc and recc.summary:
            self._detail.addWidget(label(recc.summary, "Muted", wrap=True))

        if recc and recc.team:
            self._detail.addWidget(label(LANG.m(STR, "team"), "H2"))
            for pick in recc.team:
                self._detail.addWidget(self._pick_card(pick))

        if recc and recc.upgrade_order:
            self._detail.addWidget(label(LANG.m(STR, "upgrade"), "H2"))
            for step in recc.upgrade_order:
                self._detail.addWidget(label(f"• {step}", "Muted", wrap=True))

        self._detail.addStretch(1)

    def _pick_card(self, pick) -> QWidget:
        box = card()
        lay = vbox(box, margins=(12, 10, 12, 10), spacing=4)
        reso = self._reso.get(str(pick.resonator_id))
        name = LANG.name(reso) if reso else pick.resonator_id
        role = LANG.m(STR, pick.role) if pick.role else ""
        head = f"{name}  ·  {role}" if role else name
        if pick.weapon and pick.weapon.id:
            w = self._weap.get(str(pick.weapon.id))
            if w:
                head += f"  ·  {LANG.name(w)}"
        lay.addWidget(label(head, "H2", wrap=True))
        if pick.reason:
            lay.addWidget(label(pick.reason, "Muted", wrap=True))
        return box

    # --- 삭제(사용자 확인 후) ---------------------------------------------
    def _confirm_delete(self, rec_id: str) -> None:
        ans = QMessageBox.question(
            self, LANG.m(STR, "delete"), LANG.m(STR, "confirm"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ans != QMessageBox.Yes:
            return
        engine.ai_delete(rec_id)
        if self._selected == rec_id:
            self._clear_detail()
        self.refresh()

    def retranslate(self) -> None:
        self._title.setText(LANG.m(STR, "title"))
        self._empty.setText(LANG.m(STR, "empty"))
        if self._selected:
            self._render_detail(engine.ai_get(self._selected))
        else:
            self._clear_detail()


def _delete_button(text: str):
    from PySide6.QtWidgets import QPushButton

    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    return b


if __name__ == "__main__":  # smoke: build + retranslate all langs headless
    import os
    import sys
    import tempfile

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp())
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")

    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    tab = HistoryTab()
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        tab.retranslate()
    app.processEvents()
    print("history ok")
