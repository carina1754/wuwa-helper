"""AI 코치 탭 — 프로필 인테이크 + 대화 + 빌드 추천 저장.

engine.ai_chat 은 네트워크(NVIDIA) 호출 → QThread 로 분리(UI 안 멈춤).
AI 프롬프트/추천 텍스트는 한국어(엔진 규약). 화면 라벨만 현지화.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QWidget,
)

from .. import engine
from ..lang import LANG
from ..widgets import FlowLayout, card, chip, clear_layout, hbox, hsep, label, vbox

STR = {
    "ko": {
        "title": "AI 빌딩", "profile": "내 프로필", "union": "유니온 레벨",
        "pick": "공명자 선택 (최대 3명)", "play_style": "플레이 성향",
        "style_meta": "메타/고점", "style_fun": "애정캐 위주", "style_balanced": "밸런스", "style_free": "자유롭게",
        "send": "보내기", "chat_ph": "메시지를 입력하세요…", "thinking": "생각 중…",
        "rec": "추천 빌드", "team": "추천 팀", "upgrade": "성장 우선순위", "save": "저장", "saved": "저장됨",
        "weapon": "무기", "echo": "에코", "main": "메인", "sub": "추옵", "no_key_hint": "설정 탭에서 API 키를 넣으면 실제 AI를 사용합니다.",
        "main_dps": "메인 딜러", "sub_dps": "서브 딜러", "support": "서포터", "healer": "힐러",
    },
    "en": {
        "title": "AI Coach", "profile": "My Profile", "union": "Union Level",
        "pick": "Select Resonators (up to 3)", "play_style": "Play Style",
        "style_meta": "Meta / Ceiling", "style_fun": "Favorites", "style_balanced": "Balanced", "style_free": "Flexible",
        "send": "Send", "chat_ph": "Type a message…", "thinking": "Thinking…",
        "rec": "Recommended Build", "team": "Team", "upgrade": "Upgrade Priority", "save": "Save", "saved": "Saved",
        "weapon": "Weapon", "echo": "Echo", "main": "Main", "sub": "Subs", "no_key_hint": "Add an API key in Settings to use the real AI.",
        "main_dps": "Main DPS", "sub_dps": "Sub DPS", "support": "Support", "healer": "Healer",
    },
    "ja": {
        "title": "AIコーチ", "profile": "プロフィール", "union": "ユニオンレベル",
        "pick": "共鳴者を選択（最大3名）", "play_style": "プレイ傾向",
        "style_meta": "メタ/火力", "style_fun": "推し優先", "style_balanced": "バランス", "style_free": "自由",
        "send": "送信", "chat_ph": "メッセージを入力…", "thinking": "考え中…",
        "rec": "おすすめビルド", "team": "編成", "upgrade": "育成優先度", "save": "保存", "saved": "保存しました",
        "weapon": "武器", "echo": "エコー", "main": "メイン", "sub": "サブ", "no_key_hint": "設定でAPIキーを入れると実AIを使用します。",
        "main_dps": "メインアタッカー", "sub_dps": "サブアタッカー", "support": "サポーター", "healer": "ヒーラー",
    },
    "zhHans": {
        "title": "AI教练", "profile": "我的资料", "union": "联盟等级",
        "pick": "选择共鸣者（最多3名）", "play_style": "游玩风格",
        "style_meta": "版本强度", "style_fun": "喜好优先", "style_balanced": "平衡", "style_free": "自由",
        "send": "发送", "chat_ph": "输入消息…", "thinking": "思考中…",
        "rec": "推荐配装", "team": "推荐队伍", "upgrade": "养成优先级", "save": "保存", "saved": "已保存",
        "weapon": "武器", "echo": "声骸", "main": "主属性", "sub": "副属性", "no_key_hint": "在设置中填入 API 密钥即可使用真实 AI。",
        "main_dps": "主C", "sub_dps": "副C", "support": "辅助", "healer": "治疗",
    },
}
_STYLES = ["style_meta", "style_fun", "style_balanced", "style_free"]


def _name_map(loader) -> dict:
    return {str(it["id"]): it for it in loader()}


class ChipPicker(QWidget):
    """공명자 다중 선택(칩, 최대 max_sel명). FlowLayout으로 가로 넘치면 줄바꿈(반응형).

    selected() → 선택된 ko 이름 리스트. 초과 체크는 즉시 해제.
    """

    def __init__(self, max_sel: int = 3) -> None:
        super().__init__()
        self._max = max_sel
        lay = FlowLayout(self, spacing=6)
        self._resos = engine.resonators()
        self._chips: list[tuple[QPushButton, str]] = []
        for r in self._resos:
            b = chip("")
            b.toggled.connect(self._enforce_max)
            lay.addWidget(b)
            self._chips.append((b, r["name"]))  # 값 = ko 이름(엔진 규약)
        self.retranslate()

    def _enforce_max(self, checked: bool) -> None:
        # 최대 인원 초과 시 방금 체크한 칩을 신호 차단 상태로 되돌림(재귀 방지)
        if checked and len(self.selected()) > self._max:
            b = self.sender()
            b.blockSignals(True)
            b.setChecked(False)
            b.blockSignals(False)

    def selected(self) -> list[str]:
        return [ko for b, ko in self._chips if b.isChecked()]

    def retranslate(self) -> None:
        for (b, _ko), r in zip(self._chips, self._resos):
            b.setText(LANG.name(r))


class _ChatWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, request) -> None:
        super().__init__()
        self._req = request

    def run(self) -> None:
        try:
            self.done.emit(engine.ai_chat(self._req))
        except Exception as exc:  # noqa: BLE001 — surface to chat
            self.failed.emit(str(exc))


class AiTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._resos = _name_map(engine.resonators)
        self._weapons = _name_map(engine.weapons)
        self._echoes = _name_map(engine.echoes)
        self._sonatas = _name_map(engine.sonata_sets)
        self._messages: list[dict] = []  # {"role","content"}
        self._last_rec = None
        self._worker: _ChatWorker | None = None

        root = vbox(self, margins=(16, 16, 16, 12), spacing=10)
        self._title = label("", "H1")
        root.addWidget(self._title)

        # 프로필 인테이크
        prof = card()
        pl = vbox(prof, margins=(16, 14, 16, 14), spacing=8)
        self._prof_lb = label("", "H2")
        pl.addWidget(self._prof_lb)
        row = hbox(spacing=10)
        self._union_lb = label("")
        self._union = QSpinBox()
        self._union.setRange(1, 90)
        self._union.setValue(60)
        row.addWidget(self._union_lb)
        row.addWidget(self._union)
        self._style_lb = label("")
        self._style = QComboBox()
        row.addWidget(self._style_lb)
        row.addWidget(self._style, 1)
        pl.addLayout(row)
        self._pick_lb = label("")
        pl.addWidget(self._pick_lb)
        self._picker = ChipPicker()
        pl.addWidget(self._picker)
        root.addWidget(prof)

        # 채팅 영역 — 카드 박스(로그 + 안내 + 입력줄 묶음)
        chat_box = card()
        cl = vbox(chat_box, margins=(14, 12, 14, 12), spacing=8)
        self._log_scroll = QScrollArea()
        self._log_scroll.setWidgetResizable(True)
        log_host = QWidget()
        self._log = vbox(log_host, margins=(4, 4, 4, 4), spacing=8)
        self._log.addStretch(1)
        self._log_scroll.setWidget(log_host)
        cl.addWidget(self._log_scroll, 1)

        self._hint = label("", "Faint")
        cl.addWidget(self._hint)

        bar = hbox(spacing=8)
        self._input = QLineEdit()
        self._input.setObjectName("ChatInput")  # 카드 위에서도 또렷한 입력칸
        self._input.returnPressed.connect(self._send)
        self._send_btn = QPushButton()
        self._send_btn.setObjectName("Accent")
        self._send_btn.clicked.connect(self._send)
        bar.addWidget(self._input, 1)
        bar.addWidget(self._send_btn)
        cl.addLayout(bar)
        root.addWidget(chat_box, 1)

        self.retranslate()

    # --- profile ------------------------------------------------------------
    def _build_profile(self):
        from src.models import AiProfile

        # LLM이 중국어 등으로 새는 것 방지: 프로필 note는 매 요청 시스템 프롬프트에 실림
        # (메모 입력칸은 폐기 — 하단 채팅 입력으로 충분)
        return AiProfile(
            union_level=self._union.value(),
            owned_characters=self._picker.selected(),
            desired_characters=[],  # UI 폐기 — 요청 스키마 호환용 빈 리스트
            play_style=LANG.m(STR, self._style.currentData() or _STYLES[0]),
            note="반드시 한국어로만 답변하세요.",
        )

    # --- chat ---------------------------------------------------------------
    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or (self._worker and self._worker.isRunning()):
            return
        self._input.clear()
        self._append_bubble("user", text)
        self._messages.append({"role": "user", "content": text})
        self._set_busy(True)

        req = engine.AiChatRequest(
            messages=[self._to_msg(m) for m in self._messages],
            profile=self._build_profile(),
        )
        self._worker = _ChatWorker(req)
        self._worker.done.connect(self._on_reply)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    @staticmethod
    def _to_msg(m: dict):
        from src.models import AiMessage

        return AiMessage(role=m["role"], content=m["content"])

    def _on_reply(self, resp) -> None:
        self._set_busy(False)
        self._append_bubble("assistant", resp.reply)
        self._messages.append({"role": "assistant", "content": resp.reply})
        if resp.recommendation:
            self._last_rec = resp.recommendation
            self._append_recommendation(resp.recommendation)

    def _on_fail(self, msg: str) -> None:
        self._set_busy(False)
        self._append_bubble("assistant", f"⚠ {msg}")

    def _set_busy(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._input.setEnabled(not busy)
        self._hint.setText(LANG.m(STR, "thinking") if busy else LANG.m(STR, "no_key_hint"))

    # --- render -------------------------------------------------------------
    def _append_bubble(self, role: str, text: str) -> None:
        # 채팅이 카드 안이라 내 메시지=파랑 틴트, AI=톤 박스로 구분
        box = card("BubbleMe" if role == "user" else "Card2")
        bl = vbox(box, margins=(12, 10, 12, 10))
        bl.addWidget(label(text, wrap=True))
        wrap = hbox()
        if role == "user":
            wrap.addStretch(1)
            wrap.addWidget(box, 3)
        else:
            wrap.addWidget(box, 3)
            wrap.addStretch(1)
        self._log.insertLayout(self._log.count() - 1, wrap)
        self._scroll_bottom()

    def _append_recommendation(self, rec) -> None:
        box = card()
        bl = vbox(box, margins=(16, 14, 16, 14), spacing=8)
        bl.addWidget(label(LANG.m(STR, "rec"), "H2"))
        if rec.summary:
            bl.addWidget(label(rec.summary, "Muted", wrap=True))
        if rec.team:
            bl.addWidget(hsep())
            bl.addWidget(label(LANG.m(STR, "team"), "Accent"))
            for pick in rec.team:
                bl.addWidget(self._team_line(pick))
        if rec.upgrade_order:
            bl.addWidget(hsep())
            bl.addWidget(label(LANG.m(STR, "upgrade"), "Accent"))
            for i, u in enumerate(rec.upgrade_order, 1):
                bl.addWidget(label(f"{i}. {u}", "Muted", wrap=True))
        save = QPushButton(LANG.m(STR, "save"))
        save.setObjectName("Accent")
        save.clicked.connect(lambda _c, r=rec, btn=save: self._save(r, btn))
        bl.addWidget(save, 0, Qt.AlignLeft)
        wrap = hbox()
        wrap.addWidget(box, 1)
        self._log.insertLayout(self._log.count() - 1, wrap)
        self._scroll_bottom()

    def _team_line(self, pick) -> QWidget:
        reso = self._resos.get(str(pick.resonator_id))
        name = LANG.name(reso) if reso else str(pick.resonator_id)
        parts = [name]
        if pick.role:  # LLM 은 영문 역할 키(main_dps 등) — 화면엔 현지화명
            parts.append(LANG.m(STR, pick.role) if pick.role in STR["ko"] else str(pick.role))
        if pick.weapon and pick.weapon.id:
            w = self._weapons.get(str(pick.weapon.id))
            if w:
                parts.append(f"{LANG.m(STR,'weapon')}: {LANG.name(w)}")
        text = "  ·  ".join(parts)
        w = QWidget()
        wl = vbox(w, spacing=2)
        wl.addWidget(label(text, "Gold"))
        if pick.reason:
            wl.addWidget(label(pick.reason, "Muted", wrap=True))
        if pick.echo and (pick.echo.sonata_ids or pick.echo.main_stats):
            bits = []
            if pick.echo.main_echo_id:  # 메인 에코는 id 대신 이름
                e = self._echoes.get(str(pick.echo.main_echo_id))
                if e:
                    bits.append(LANG.name(e))
            if pick.echo.sonata_ids:  # 소나타 세트 id(s-xxx) → 세트 이름
                names = [LANG.name(s) for sid in pick.echo.sonata_ids if (s := self._sonatas.get(str(sid)))]
                bits.append(", ".join(names) if names else ", ".join(pick.echo.sonata_ids))
            if pick.echo.main_stats:
                bits.append(f"{LANG.m(STR,'main')} " + ", ".join(f"{k}:{v}" for k, v in pick.echo.main_stats.items()))
            if pick.echo.sub_stats:
                bits.append(f"{LANG.m(STR,'sub')} " + ", ".join(pick.echo.sub_stats))
            wl.addWidget(label(f"{LANG.m(STR,'echo')} — " + " / ".join(bits), "Faint", wrap=True))
        return w

    def _save(self, rec, btn: QPushButton) -> None:
        record = engine.AiRecommendationRecord(
            id=uuid.uuid4().hex,
            created_at=datetime.now(timezone.utc).isoformat(),
            profile=self._build_profile(),
            conversation=[self._to_msg(m) for m in self._messages],
            recommendation=rec,
            title=(rec.summary[:40] if rec.summary else None),
        )
        engine.ai_save(record)
        btn.setText(LANG.m(STR, "saved"))
        btn.setEnabled(False)

    def _scroll_bottom(self) -> None:
        bar = self._log_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def retranslate(self) -> None:
        self._title.setText(LANG.m(STR, "title"))
        self._prof_lb.setText(LANG.m(STR, "profile"))
        self._union_lb.setText(LANG.m(STR, "union"))
        self._style_lb.setText(LANG.m(STR, "play_style"))
        self._pick_lb.setText(LANG.m(STR, "pick"))
        self._send_btn.setText(LANG.m(STR, "send"))
        self._input.setPlaceholderText(LANG.m(STR, "chat_ph"))
        if not (self._worker and self._worker.isRunning()):
            self._hint.setText(LANG.m(STR, "no_key_hint"))
        cur = self._style.currentData()
        self._style.blockSignals(True)
        self._style.clear()
        for key in _STYLES:
            self._style.addItem(LANG.m(STR, key), key)
        if cur:
            i = _STYLES.index(cur) if cur in _STYLES else 0
            self._style.setCurrentIndex(i)
        self._style.blockSignals(False)
        self._picker.retranslate()


if __name__ == "__main__":  # smoke: build + max-3 chip enforce + mock chat (no key → engine mock reply)
    import os
    import sys
    import tempfile

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp())
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    t = AiTab()
    # 최대 3명 강제: 3개 체크 후 4번째 체크는 즉시 해제
    chips = [b for b, _ko in t._picker._chips]
    for b in chips[:3]:
        b.setChecked(True)
    chips[3].setChecked(True)
    assert not chips[3].isChecked() and len(t._picker.selected()) == 3
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        t.retranslate()
    LANG.set("ko")
    # profile builds + one mock turn (no API key → ai_coach returns Korean stub)
    prof = t._build_profile()
    assert prof.union_level == 60 and len(prof.owned_characters) == 3 and prof.desired_characters == []
    assert "한국어" in (prof.note or "")  # 한국어 강제 지시 포함
    resp = engine.ai_chat(engine.AiChatRequest(messages=[t._to_msg({"role": "user", "content": "추천해줘"})], profile=prof))
    assert resp.reply
    print("ai ok")
