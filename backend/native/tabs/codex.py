"""도감 탭 — 공명자/무기/에코 그리드 + 검색·필터 + 상세 다이얼로그.

표시 전용(카탈로그 직접 읽기). 스탯 커브는 클라 보간(딜 아님, 화면값).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QScrollArea,
    QWidget,
)

from .. import engine
from ..lang import LANG
from ..widgets import (
    IconTile,
    chip,
    clear_layout,
    flow_of,
    hbox,
    hsep,
    label,
    vbox,
    GridCell,
    LabeledSlider,
)

STR = {
    "ko": {"forte": "포르테 보너스", "chain": "공명 사슬", "skills": "스킬",
           "base_stats": "기본 능력치", "no_result": "결과 없음", "cost": "코스트", "sonata": "소나타 세트"},
    "en": {"forte": "Forte Bonus", "chain": "Resonance Chain", "skills": "Skills",
           "base_stats": "Base Stats", "no_result": "No results", "cost": "Cost", "sonata": "Sonata Sets"},
    "ja": {"forte": "フォルテボーナス", "chain": "共鳴チェーン", "skills": "スキル",
           "base_stats": "基礎ステータス", "no_result": "結果なし", "cost": "コスト", "sonata": "ソナタセット"},
    "zhHans": {"forte": "声骸加成", "chain": "共鸣链", "skills": "技能",
               "base_stats": "基础属性", "no_result": "无结果", "cost": "费用", "sonata": "声骸套装"},
}

# 기본 스탯 → StatKey (현지화 라벨용)
_BASE_STAT_KEY = {"Life": "hp", "Atk": "atk", "Def": "def", "Crit": "crit", "CritDamage": "critDmg"}


def _curve_value(curve: list, level: int) -> float:
    """레벨별 스탯값. 정렬된 curve 에서 level 이하 마지막(승급 후) 값."""
    best = None
    for pt in curve:
        if pt["level"] <= level:
            best = pt["value"]
        else:
            break
    if best is None:
        return curve[0]["value"] if curve else 0
    return best


# --- 상세 다이얼로그 ---------------------------------------------------------
class _Detail(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.resize(560, 720)
        outer = vbox(self, margins=(0, 0, 0, 0))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._host = QWidget()
        self.body = vbox(self._host, margins=(22, 22, 22, 22), spacing=12)
        scroll.setWidget(self._host)
        outer.addWidget(scroll)


class ResonatorDetail(_Detail):
    def __init__(self, reso: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(LANG.name(reso))
        head = hbox(spacing=14)
        head.addWidget(IconTile("characters", reso["id"], reso.get("rarity"), 96))
        htxt = vbox(spacing=4)
        htxt.addWidget(label(LANG.name(reso), "H1"))
        sub = " · ".join(x for x in [
            LANG.element(reso.get("element", "")),
            LANG.weapon_type(reso.get("weapon_type_ko", "")),
            reso.get("role") or "",
            f"{reso.get('rarity')}★",
        ] if x)
        htxt.addWidget(label(sub, "Muted"))
        head.addLayout(htxt)
        head.addStretch(1)
        self.body.addLayout(head)
        self.body.addWidget(hsep())

        # 레벨 슬라이더 → 기본 스탯
        self.body.addWidget(label(LANG.m(STR, "base_stats"), "H2"))
        self._lvl = LabeledSlider(LANG.t("level"), 1, reso.get("max_level", 90), reso.get("max_level", 90))
        self.body.addWidget(self._lvl)
        self._stat_rows = QWidget()
        self._stat_lay = vbox(self._stat_rows, spacing=3)
        self.body.addWidget(self._stat_rows)
        self._reso = reso
        self._lvl.valueChanged.connect(self._render_stats)
        self._render_stats(self._lvl.value())

        fb = reso.get("forte_bonus") or {}
        if fb:
            parts = ", ".join(f"{LANG.stat(k)} +{v}%" for k, v in fb.items())
            self.body.addWidget(label(f"{LANG.m(STR,'forte')}: {parts}", "Accent", wrap=True))

        # 스킬 레벨 슬라이더 → 스킬 배율
        self.body.addWidget(hsep())
        self.body.addWidget(label(LANG.m(STR, "skills"), "H2"))
        self._sk_lvl = LabeledSlider(LANG.t("skill"), 1, 10, 10)
        self.body.addWidget(self._sk_lvl)
        self._skills_box = QWidget()
        self._skills_lay = vbox(self._skills_box, spacing=10)
        self.body.addWidget(self._skills_box)
        self._sk_lvl.valueChanged.connect(self._render_skills)
        self._render_skills(10)

        # 공명 사슬
        chain = reso.get("resonance_chain") or []
        if chain:
            self.body.addWidget(hsep())
            self.body.addWidget(label(LANG.m(STR, "chain"), "H2"))
            for i, node in enumerate(chain, 1):
                self.body.addWidget(label(f"S{i}. {LANG.field(node, 'NodeName')}", "Muted", wrap=True))
        self.body.addStretch(1)

    def _render_stats(self, level: int) -> None:
        clear_layout(self._stat_lay)
        curves = self._reso.get("stat_curves") or {}
        for raw, key in _BASE_STAT_KEY.items():
            curve = curves.get(raw) or []
            if not curve:
                continue
            val = _curve_value(curve, level)
            txt = f"{val:.0f}%" if raw in ("Crit", "CritDamage") else f"{round(val):,}"
            row = hbox()
            row.addWidget(label(LANG.stat(key), "Muted"))
            row.addStretch(1)
            row.addWidget(label(txt, "Gold"))
            self._stat_lay.addLayout(row)

    def _render_skills(self, sk_level: int) -> None:
        clear_layout(self._skills_lay)
        idx = sk_level - 1
        for sk in self._reso.get("skills") or []:
            block = vbox(spacing=3)
            title = f"{LANG.field(sk, 'SkillName')}  ·  {LANG.skill_type(sk.get('SkillType'))}"
            block.addWidget(label(title, "Accent", wrap=True))
            for dmg in sk.get("damage") or []:
                rates = dmg.get("rates") or []
                rate = rates[idx] if idx < len(rates) else (rates[-1] if rates else "")
                if rate:
                    r = hbox()
                    r.addWidget(label(dmg.get("name", ""), "Muted"))
                    r.addStretch(1)
                    r.addWidget(label(rate, "Faint"))
                    block.addLayout(r)
            self._skills_lay.addLayout(block)


class WeaponDetail(_Detail):
    def __init__(self, weapon: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(LANG.name(weapon))
        self._w = weapon
        head = hbox(spacing=14)
        head.addWidget(IconTile("weapons", weapon["id"], weapon.get("rarity"), 84))
        htxt = vbox(spacing=4)
        htxt.addWidget(label(LANG.name(weapon), "H1"))
        htxt.addWidget(label(f"{LANG.weapon_type(weapon.get('weapon_type_ko',''))} · {weapon.get('rarity')}★", "Muted"))
        head.addLayout(htxt)
        head.addStretch(1)
        self.body.addLayout(head)
        self.body.addWidget(hsep())

        self._lvl = LabeledSlider(LANG.t("level"), 1, 90, 90)
        self.body.addWidget(self._lvl)
        self._props = QWidget()
        self._props_lay = vbox(self._props, spacing=3)
        self.body.addWidget(self._props)
        self._lvl.valueChanged.connect(self._render_props)
        self._render_props(90)

        desc = LANG.field(weapon, "desc") or weapon.get("attributes_description") or ""
        if desc:
            self.body.addWidget(hsep())
            self.body.addWidget(label(desc, "Muted", wrap=True))
        self.body.addStretch(1)

    def _render_props(self, level: int) -> None:
        clear_layout(self._props_lay)
        for p in self._w.get("properties") or []:
            curve = p.get("curve") or []
            val = _curve_value(curve, level) if curve else p.get("base", 0)
            name = p.get("name", "")
            pct = "%" in str(name) or (val and val < 100 and "." in f"{val}")
            txt = f"{val:.1f}%" if pct else f"{round(val):,}"
            row = hbox()
            row.addWidget(label(str(name), "Muted"))
            row.addStretch(1)
            row.addWidget(label(txt, "Gold"))
            self._props_lay.addLayout(row)


class EchoDetail(_Detail):
    def __init__(self, echo: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(LANG.name(echo))
        head = hbox(spacing=14)
        head.addWidget(IconTile("echoes", echo["id"], echo.get("rarity"), 84))
        htxt = vbox(spacing=4)
        htxt.addWidget(label(LANG.name(echo), "H1"))
        htxt.addWidget(label(f"{LANG.m(STR,'cost')} {echo.get('cost')} · {LANG.element(echo.get('element',''))}", "Muted"))
        head.addLayout(htxt)
        head.addStretch(1)
        self.body.addLayout(head)
        self.body.addWidget(hsep())

        sonata = echo.get("sonata") or []
        if sonata:
            self.body.addWidget(label(f"{LANG.m(STR,'sonata')}: {', '.join(sonata)}", "Accent", wrap=True))
        from ..lang import strip_tags
        skill = echo.get("skill") or {}
        desc = strip_tags(skill.get("DescriptionEx"))
        if desc:
            self.body.addWidget(hsep())
            self.body.addWidget(label(desc, "Muted", wrap=True))
        self.body.addStretch(1)


# --- 메인 탭 -----------------------------------------------------------------
_MODES = [
    ("codex_resonators", "characters", engine.resonators, "element", ResonatorDetail),
    ("codex_weapons", "weapons", engine.weapons, "weapon_type_ko", WeaponDetail),
    ("codex_echoes", "echoes", engine.echoes, "cost", EchoDetail),
]


class CodexTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._mode = 0
        self._rarity_filter: int | None = None
        self._facet_filter = None

        root = vbox(self, margins=(16, 16, 16, 8), spacing=10)

        # 모드 전환(공명자/무기/에코)
        self._mode_row = hbox(spacing=6)
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_btns = []
        for i, (key, *_rest) in enumerate(_MODES):
            b = chip("", checkable=True)
            b.setChecked(i == 0)
            b.clicked.connect(lambda _c, idx=i: self._set_mode(idx))
            self._mode_group.addButton(b, i)
            self._mode_btns.append(b)
            self._mode_row.addWidget(b)
        self._mode_row.addStretch(1)
        self._search = QLineEdit()
        self._search.setMaximumWidth(240)
        self._search.textChanged.connect(lambda _t: self._render_grid())
        self._mode_row.addWidget(self._search)
        root.addLayout(self._mode_row)

        # 필터 칩(레어리티 + facet)
        self._filter_host = QWidget()
        self._filter_lay = hbox(self._filter_host, spacing=6)
        root.addWidget(self._filter_host)

        # 그리드(스크롤)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid_outer = vbox(self._grid_host, margins=(0, 4, 0, 0))
        scroll.setWidget(self._grid_host)
        root.addWidget(scroll, 1)

        self.retranslate()

    # --- state --------------------------------------------------------------
    def _set_mode(self, idx: int) -> None:
        self._mode = idx
        self._rarity_filter = None
        self._facet_filter = None
        self._build_filters()
        self._render_grid()

    def _items(self) -> list[dict]:
        return _MODES[self._mode][2]()

    def _facet_key(self) -> str:
        return _MODES[self._mode][3]

    def _build_filters(self) -> None:
        clear_layout(self._filter_lay)
        items = self._items()
        # 레어리티 칩
        rarities = sorted({it.get("rarity") for it in items if it.get("rarity")}, reverse=True)
        # exclusive 그룹은 재클릭 해제가 안 됨 → 비배타 + 핸들러에서 나머지 끄기(토글 가능)
        rg = QButtonGroup(self._filter_host)
        rg.setExclusive(False)
        for r in rarities:
            b = chip(f"{r}★")
            b.toggled.connect(lambda on, rr=r, btn=b: self._on_rarity(rr, on, btn))
            rg.addButton(b)
            self._filter_lay.addWidget(b)
        self._filter_lay.addSpacing(10)
        # facet 칩
        fk = self._facet_key()
        vals = sorted({it.get(fk) for it in items if it.get(fk) is not None},
                      key=lambda x: (str(type(x)), x))
        fg = QButtonGroup(self._filter_host)
        fg.setExclusive(False)
        for v in vals:
            b = chip(self._facet_label(fk, v))
            b.toggled.connect(lambda on, vv=v, btn=b: self._on_facet(vv, on, btn))
            fg.addButton(b)
            self._filter_lay.addWidget(b)
        self._filter_lay.addStretch(1)
        self._rarity_group = rg
        self._facet_group = fg

    def _facet_label(self, key: str, value) -> str:
        if key == "element":
            return LANG.element(value)
        if key == "weapon_type_ko":
            return LANG.weapon_type(value)
        if key == "cost":
            return f"{LANG.m(STR,'cost')} {value}"
        return str(value)

    def _on_rarity(self, rarity: int, on: bool, btn=None) -> None:
        if on:
            # 수동 배타: 다른 칩을 먼저 끔(toggled(False)→필터 None 덮음) → 마지막에 내 값 대입
            for b in self._rarity_group.buttons():
                if b is not btn and b.isChecked():
                    b.setChecked(False)
        self._rarity_filter = rarity if on else None
        self._render_grid()

    def _on_facet(self, value, on: bool, btn=None) -> None:
        if on:
            # 수동 배타: 위와 동일 순서(끄기 먼저, 대입 마지막)
            for b in self._facet_group.buttons():
                if b is not btn and b.isChecked():
                    b.setChecked(False)
        self._facet_filter = value if on else None
        self._render_grid()

    # --- grid ---------------------------------------------------------------
    def _render_grid(self) -> None:
        clear_layout(self._grid_outer)
        _key, kind, _loader, fk, detail_cls = _MODES[self._mode]
        q = self._search.text().strip().lower()
        cells = []
        for it in self._items():
            if self._rarity_filter and it.get("rarity") != self._rarity_filter:
                continue
            if self._facet_filter is not None and it.get(fk) != self._facet_filter:
                continue
            if q and not self._matches(it, q):
                continue
            cell = GridCell(kind, it["id"], it.get("rarity"), LANG.name(it))
            cell.clicked.connect(lambda _id, item=it, cls=detail_cls: self._open_detail(cls, item))
            cells.append(cell)
        if not cells:
            self._grid_outer.addWidget(label(LANG.m(STR, "no_result"), "Muted"))
        else:
            self._grid_outer.addWidget(flow_of(cells))  # 창 폭 따라 줄바꿈(반응형)
        self._grid_outer.addStretch(1)

    def _matches(self, item: dict, q: str) -> bool:
        for f in ("name", "name_en", "name_ja", "name_zhHans", "name_ko"):
            if q in str(item.get(f, "")).lower():
                return True
        return False

    def _open_detail(self, cls, item) -> None:
        dlg = cls(item, self)
        dlg.exec()

    def retranslate(self) -> None:
        for b, (key, *_r) in zip(self._mode_btns, _MODES):
            b.setText(LANG.t(key))
        self._search.setPlaceholderText(LANG.t("search"))
        self._build_filters()
        self._render_grid()


if __name__ == "__main__":  # smoke
    import os
    import sys

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    t = CodexTab()
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        t.retranslate()
    # open one of each detail
    ResonatorDetail(engine.resonators()[0])
    WeaponDetail(engine.weapons()[0])
    EchoDetail(engine.echoes()[0])
    app.processEvents()
    # 필터 칩 토글: 적용 → 재클릭 해제 → 다른 칩 클릭 시 수동 배타
    LANG.set("ko")
    t.retranslate()
    total = len(t._items())
    c5 = next(b for b in t._rarity_group.buttons() if b.text() == "5★")
    c4 = next(b for b in t._rarity_group.buttons() if b.text() == "4★")
    c5.click()
    assert t._rarity_filter == 5 and c5.isChecked()
    assert len(t._grid_host.findChildren(GridCell)) == sum(
        1 for it in t._items() if it.get("rarity") == 5
    )
    c5.click()  # 재클릭 → 해제 + 전체 노출
    assert t._rarity_filter is None and not c5.isChecked()
    assert len(t._grid_host.findChildren(GridCell)) == total
    c5.click()
    c4.click()  # 수동 배타: 5★ 자동 해제
    assert t._rarity_filter == 4 and c4.isChecked() and not c5.isChecked()
    print("codex ok")
