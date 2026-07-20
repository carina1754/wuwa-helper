"""픽업 일정 탭 — 배너 단위 그룹 카드(pickup_banners 정본).

필터 칩: 캐릭터/무기/콜라보 멀티 토글(기본 전부 켬, 끄면 해당 종류 숨김).
섹션: 진행중/예정/종료. 배너 카드 = 헤더행(배너명+기간+상태필) → 버전 → 구분선
→ FlowLayout 엔트리(아이콘 32 + 이름 + 배지, 가로 배치·넘치면 줄바꿈).
복각 차수(1차 복각 등)는 pickup_schedule 을 (name_en, version, phase) 로 조인해 표시.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QWidget

from .. import engine, icons
from ..lang import LANG
from ..widgets import card, chip, clear_layout, flow_of, hbox, hsep, label, vbox

STR = {
    "ko": {
        "title": "픽업 일정", "f_char": "캐릭터", "f_weapon": "무기", "f_collab": "콜라보",
        "g_live": "진행중", "g_soon": "예정", "g_ended": "종료", "ended": "종료",
        "new": "신규", "rerun": "복각", "collab": "콜라보", "none": "해당 없음",
    },
    "en": {
        "title": "Pickup Banners", "f_char": "Characters", "f_weapon": "Weapons", "f_collab": "Collab",
        "g_live": "Live", "g_soon": "Upcoming", "g_ended": "Ended", "ended": "Ended",
        "new": "New", "rerun": "Rerun", "collab": "Collab", "none": "Nothing here",
    },
    "ja": {
        "title": "ピックアップ", "f_char": "キャラ", "f_weapon": "武器", "f_collab": "コラボ",
        "g_live": "開催中", "g_soon": "予定", "g_ended": "終了", "ended": "終了",
        "new": "新規", "rerun": "復刻", "collab": "コラボ", "none": "該当なし",
    },
    "zhHans": {
        "title": "卡池", "f_char": "角色", "f_weapon": "武器", "f_collab": "联动",
        "g_live": "进行中", "g_soon": "预定", "g_ended": "已结束", "ended": "已结束",
        "new": "新增", "rerun": "复刻", "collab": "联动", "none": "无",
    },
}

_FILTERS = [("char", "f_char"), ("weapon", "f_weapon"), ("collab", "f_collab")]
_GROUPS = [("live", "g_live"), ("soon", "g_soon"), ("ended", "g_ended")]


def _parse(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s[:10]) if s else None
    except ValueError:
        return None


def _md(d: date) -> str:
    return f"{d.month}.{d.day}"


def _side(raw: str | None) -> str:
    d = _parse(raw)
    return _md(d) if d else (raw or "")


def _digit(s) -> str:
    return "".join(ch for ch in str(s or "") if ch.isdigit())


class PickupTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        # (name_en, version[, phase]) → 복각 차수 라벨(스케줄 정본 조인)
        id2en = {str(r["id"]): (r.get("name_en") or "").strip().lower() for r in engine.resonators()}
        self._cat_label: dict[tuple, str] = {}
        for it in engine.pickup_schedule():
            for name in (it.characters or []):
                k = (name.strip().lower(), it.version or "", _digit(it.phase))
                self._cat_label.setdefault(k, it.label_ko or "")
                self._cat_label.setdefault(k[:2], it.label_ko or "")

        today = date.today()
        self._banners: list[dict] = []
        for b in engine.pickup_banners():
            s, e = _parse(b.start_date), _parse(b.end_date)
            if e and e < today:
                kind, dday = "ended", 0
            elif s and s > today:
                kind, dday = "soon", (s - today).days
            elif e:
                kind, dday = "live", (e - today).days
            else:
                kind, dday = "ended", 0
            self._banners.append({"b": b, "s": s, "e": e, "kind": kind, "dday": dday, "id2en": id2en})
        # 멀티 토글 필터 — 끈 종류는 숨김, 기본 전부 표시
        self._active: set[str] = {k for k, _ in _FILTERS}

        outer = vbox(self, margins=(0, 0, 0, 0))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        root = vbox(host, margins=(20, 18, 20, 24), spacing=10)
        self._title = label("", "H1")
        root.addWidget(self._title)

        self._chips: list[tuple] = []
        frow = hbox(spacing=8)
        for kind, key in _FILTERS:
            c = chip("", checkable=True)
            c.setChecked(True)
            c.clicked.connect(lambda on=False, k=kind: self._toggle(k, on))
            self._chips.append((c, key))
            frow.addWidget(c)
        frow.addStretch(1)
        root.addLayout(frow)

        self._body_host = QWidget()
        self._body = vbox(self._body_host, spacing=10)
        root.addWidget(self._body_host)
        root.addStretch(1)

        scroll.setWidget(host)
        outer.addWidget(scroll)
        self.retranslate()

    def _toggle(self, kind: str, on: bool) -> None:
        if on:
            self._active.add(kind)
        else:
            self._active.discard(kind)
        self._render()

    # --- entry cells ---------------------------------------------------------
    def _icon(self, kind: str, item_id, size: int = 32) -> QLabel:
        ic = QLabel()
        ic.setFixedSize(size, size)
        ic.setScaledContents(True)
        pm = icons.catalog_pixmap(kind, item_id, size * 2)
        if not pm.isNull():
            ic.setPixmap(pm)
        return ic

    def _char_cell(self, en: dict, ch) -> QFrame:
        f = QFrame()
        f.setObjectName("Row")
        h = hbox(f, margins=(8, 5, 10, 5), spacing=8)
        h.addWidget(self._icon("characters", ch.catalog_id))
        nm = label(ch.name_ko or "", None)
        nm.setStyleSheet("font-size:14px; font-weight:600;")
        h.addWidget(nm)
        return f

    def _banner_label(self, en: dict, chars: list) -> str:
        """배너 단위 복각 차수(스케줄 조인, 첫 매치) — 없으면 신규/복각 폴백."""
        b = en["b"]
        for ch in chars:
            en_name = en["id2en"].get(str(ch.catalog_id), "")
            lbl = self._cat_label.get((en_name, b.version or "", _digit(b.phase))) or self._cat_label.get(
                (en_name, b.version or "")
            )
            if lbl:
                return lbl
        return LANG.m(STR, "rerun") if b.is_rerun else LANG.m(STR, "new")

    def _weapon_cell(self, w) -> QFrame:
        f = QFrame()
        f.setObjectName("Row")
        h = hbox(f, margins=(8, 5, 10, 5), spacing=8)
        wid = str(w.icon or "").rstrip("/").rsplit("/", 1)[-1]
        h.addWidget(self._icon("weapons", wid))
        nm = label(w.name_ko or "", None)
        nm.setStyleSheet("font-size:14px; font-weight:600;")
        h.addWidget(nm)
        # ★ 등급 생략 — 픽업 무기는 전부 5성
        if w.weapon_type:
            h.addWidget(label(w.weapon_type, "Faint"))
        return f

    def _rows(self, en: dict) -> tuple[list, list]:
        """활성 필터 기준 표시할 (캐릭, 무기) — 둘 다 비면 카드 생략."""
        b = en["b"]
        if b.is_collab:
            if "collab" not in self._active:
                return [], []
            return list(b.characters or []), list(b.weapons or [])
        chars = list(b.characters or []) if "char" in self._active else []
        weaps = list(b.weapons or []) if "weapon" in self._active else []
        return chars, weaps

    def _banner_card(self, en: dict, chars: list, weaps: list) -> QFrame:
        b = en["b"]
        box = card()
        lay = vbox(box, margins=(16, 12, 16, 10), spacing=6)

        head = hbox(spacing=8)
        nm = label(b.banner_name or "", None)  # 한 줄 고정(줄바꿈 금지)
        nm.setStyleSheet("font-size:15px; font-weight:700;")
        head.addWidget(nm)
        # 복각 차수/신규 배지는 배너명 옆 1회(캐릭별 반복 금지)
        cat = self._banner_label(en, list(b.characters or []))
        cat_pill = QLabel(cat)
        cat_pill.setObjectName("PillNew" if ("복각" not in cat and cat != LANG.m(STR, "rerun")) else "PillRerun")
        head.addWidget(cat_pill)
        if b.is_collab:
            cl = QLabel(LANG.m(STR, "collab"))
            cl.setObjectName("PillSoon")
            head.addWidget(cl)
        head.addStretch(1)
        period = f"{_side(b.start_date)} ~ {_side(b.end_date)}".strip(" ~")
        head.addWidget(label(period, "Muted"))
        pill = QLabel()
        if en["kind"] == "live":
            pill.setText(f"D-{en['dday']}")
            pill.setObjectName("PillLive")
        elif en["kind"] == "soon":
            pill.setText(f"D-{en['dday']}")
            pill.setObjectName("PillSoon")
        else:
            pill.setText(LANG.m(STR, "ended"))
            pill.setObjectName("PillEnded")
        head.addWidget(pill)
        lay.addLayout(head)

        # phase 는 게임 내 페이즈가 아니라 데이터상 배너 일련번호 → 표시 안 함(조인 키로만 사용)
        if b.version:
            lay.addWidget(label(f"v{b.version}", "Faint"))
        lay.addWidget(hsep())

        cells = [self._char_cell(en, ch) for ch in chars] + [self._weapon_cell(w) for w in weaps]
        lay.addWidget(flow_of(cells, spacing=6))
        return box

    def _section_head(self, kind: str, key: str, n: int) -> QWidget:
        """상태 컬러 도트 + 큰 볼드 제목 + 카운트 필 — 섹션 구분을 또렷하게."""
        w = QWidget()
        h = hbox(w, margins=(4, 12, 4, 2), spacing=8)
        dot = QLabel()
        dot.setObjectName({"live": "DotLive", "soon": "DotSoon", "ended": "DotEnded"}[kind])
        h.addWidget(dot)
        t = label(LANG.m(STR, key), None)
        t.setStyleSheet("font-size:17px; font-weight:800;")
        h.addWidget(t)
        cnt = QLabel(str(n))
        cnt.setObjectName({"live": "PillLive", "soon": "PillSoon", "ended": "PillEnded"}[kind])
        h.addWidget(cnt)
        h.addStretch(1)
        return w

    def _render(self) -> None:
        clear_layout(self._body)
        shown = 0
        for kind, key in _GROUPS:
            rows = []
            for en in self._banners:
                if en["kind"] != kind:
                    continue
                chars, weaps = self._rows(en)
                if chars or weaps:
                    rows.append((en, chars, weaps))
            if kind == "live":
                rows.sort(key=lambda t: (t[0]["e"] or date.max).toordinal())
            elif kind == "soon":
                rows.sort(key=lambda t: (t[0]["s"] or date.max).toordinal())
            else:
                rows.sort(key=lambda t: -((t[0]["e"] or date.min).toordinal()))
            if not rows:
                continue
            shown += len(rows)
            self._body.addWidget(self._section_head(kind, key, len(rows)))
            for en, chars, weaps in rows:
                self._body.addWidget(self._banner_card(en, chars, weaps))
        if not shown:
            self._body.addWidget(label(LANG.m(STR, "none"), "Muted"))

    def retranslate(self) -> None:
        self._title.setText(LANG.m(STR, "title"))
        for c, key in self._chips:
            c.setText(LANG.m(STR, key))
        self._render()


if __name__ == "__main__":  # smoke: build + toggle combos + retranslate all langs headless
    import os
    import sys

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")

    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    tab = PickupTab()
    assert engine.pickup_banners(), "banners empty"
    assert tab._active == {"char", "weapon", "collab"} and tab._body.count() > 1
    chips = [c for c, _ in tab._chips]
    chips[0].click()                                            # 캐릭터만 끔
    assert tab._active == {"weapon", "collab"}
    chips[1].click()
    chips[2].click()                                            # 전부 끔 → 해당 없음 1개
    assert not tab._active and tab._body.count() == 1, "all-off should show none"
    for c in chips:                                             # 전부 재활성
        c.click()
    assert tab._active == {"char", "weapon", "collab"} and tab._body.count() > 1
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        tab.retranslate()
    app.processEvents()
    print("pickup ok banners=%d" % len(tab._banners))
