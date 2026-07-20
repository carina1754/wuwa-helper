"""파티 탭 — 최대 3인 팀 딜 시뮬. 권위 엔진(engine.calculate) 단일 소스.

에코는 슬롯 5개(C4/C3/C3/C1/C1) 개별 선택 + 소나타 콤보는 세트 일괄 적용 프리셋.
서브옵션은 엔진이 배치와 무관하게 멤버 풀에 합산하므로 멤버당 한 패널로 축약.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QWidget,
)

from src.sim.formula import ELEMENT_DMG_KEY

from .. import calc, engine
from ..lang import LANG, fmt_stat
from ..theme import THEME
from ..widgets import card, chip, clear_layout, hbox, hsep, label, vbox

STR = {
    "ko": {
        "conditions": "전투 조건", "enemy_level": "적 레벨", "enemy_res": "적 저항%",
        "res_shred": "저항 감소%", "def_reduce": "방깎%", "boost": "증폭%", "party_shred": "팀 방깎%",
        "add_member": "+ 멤버 추가", "remove": "제거", "member": "멤버",
        "level": "레벨", "sequence": "공명 사슬", "weapon": "무기", "wlv": "무기 레벨",
        "rank": "정제", "skill": "스킬 레벨", "full_uptime": "풀 업타임", "sonata": "소나타",
        "mains": "메인 옵션", "subs": "서브 옵션(합산)", "calculate": "딜 계산",
        "team_total": "팀 총딜", "share": "지분", "skills": "스킬 딜", "situational": "상황부(총딜 제외)",
        "saved_history": "기록 탭에 자동 저장됨",
        "anomaly": "이상", "tune_break": "조화도 파괴", "team_buffs": "적용 팀 버프",
        "need_member": "멤버를 1명 이상 추가하세요.",
        "empty_hint": "파티를 구성하고 '딜 계산'을 누르면\n결과가 여기에 표시됩니다.",
    },
    "en": {
        "conditions": "Combat Conditions", "enemy_level": "Enemy Lv", "enemy_res": "Enemy RES%",
        "res_shred": "RES Shred%", "def_reduce": "DEF Reduce%", "boost": "Amplify%", "party_shred": "Party DEF Shred%",
        "add_member": "+ Add Member", "remove": "Remove", "member": "Member",
        "level": "Level", "sequence": "Chain", "weapon": "Weapon", "wlv": "Weapon Lv",
        "rank": "Refine", "skill": "Skill Lv", "full_uptime": "Full uptime", "sonata": "Sonata",
        "mains": "Main Stats", "subs": "Sub Stats (summed)", "calculate": "Calculate",
        "team_total": "Team Total", "share": "Share", "skills": "Skill DMG", "situational": "Situational (excl. total)",
        "saved_history": "Saved to History tab",
        "anomaly": "Anomaly", "tune_break": "Tune Break", "team_buffs": "Applied team buffs",
        "need_member": "Add at least one member.",
        "empty_hint": "Build your party and hit Calculate\nto see damage results here.",
    },
    "ja": {
        "conditions": "戦闘条件", "enemy_level": "敵レベル", "enemy_res": "敵耐性%",
        "res_shred": "耐性減少%", "def_reduce": "防御減少%", "boost": "増幅%", "party_shred": "編成防御減少%",
        "add_member": "+ メンバー追加", "remove": "削除", "member": "メンバー",
        "level": "レベル", "sequence": "共鳴チェーン", "weapon": "武器", "wlv": "武器レベル",
        "rank": "精錬", "skill": "スキルレベル", "full_uptime": "フルアップ", "sonata": "ソナタ",
        "mains": "メイン", "subs": "サブ(合算)", "calculate": "計算",
        "team_total": "編成総ダメージ", "share": "割合", "skills": "スキルダメージ", "situational": "状況(総ダメージ除外)",
        "saved_history": "履歴タブに自動保存",
        "anomaly": "異常", "tune_break": "調和度破壊", "team_buffs": "適用チームバフ",
        "need_member": "メンバーを1人以上追加してください。",
        "empty_hint": "パーティを編成して「計算」を押すと\nここに結果が表示されます。",
    },
    "zhHans": {
        "conditions": "战斗条件", "enemy_level": "敌人等级", "enemy_res": "敌人抗性%",
        "res_shred": "抗性削减%", "def_reduce": "防御削减%", "boost": "增幅%", "party_shred": "队伍防御削减%",
        "add_member": "+ 添加成员", "remove": "移除", "member": "成员",
        "level": "等级", "sequence": "共鸣链", "weapon": "武器", "wlv": "武器等级",
        "rank": "精炼", "skill": "技能等级", "full_uptime": "满打", "sonata": "合鸣",
        "mains": "主属性", "subs": "副属性(合计)", "calculate": "计算",
        "team_total": "队伍总伤害", "share": "占比", "skills": "技能伤害", "situational": "情境(不计入总伤)",
        "saved_history": "已自动保存到记录",
        "anomaly": "异常", "tune_break": "谐振破坏", "team_buffs": "生效队伍增益",
        "need_member": "请至少添加一名成员。",
        "empty_hint": "组建队伍并点击「计算」\n结果将显示在此处。",
    },
}

# 축약 서브옵션 패널: (stat key, 백분율 여부). 값은 5에코 합산 총량(유저 입력).
_SUB_KEYS = [("crit", True), ("critDmg", True), ("atkPct", True), ("atk", False)]
# 에코 슬롯 코스트(1×4 + 2×3 + 2×1) — 실전 표준.
_SLOT_COSTS = [4, 3, 3, 1, 1]


def _spin(minimum, maximum, value, decimals=0, suffix="") -> QSpinBox | QDoubleSpinBox:
    box = QDoubleSpinBox() if decimals else QSpinBox()
    box.setRange(minimum, maximum)
    if decimals:
        box.setDecimals(decimals)
    box.setValue(value)
    if suffix:
        box.setSuffix(suffix)
    box.setMaximumWidth(120)
    return box


def _labeled(text: str, w: QWidget) -> QWidget:
    row = QWidget()
    lay = hbox(row, spacing=8)
    lb = label(text, "Muted")
    lb.setMinimumWidth(96)
    lay.addWidget(lb)
    lay.addWidget(w, 1)
    return row


class _MemberEditor(QFrame):
    """멤버 한 명 빌드 에디터. build() → engine.MemberIn."""

    removed = Signal(object)
    resoChanged = Signal()

    def __init__(self, index: int) -> None:
        super().__init__()
        self.setObjectName("Card")
        self._resos = engine.resonators()
        self._weapons = engine.weapons()
        self._sonatas = engine.sonata_sets()
        self._echoes = engine.echoes()
        self._gc = engine.game_config()

        lay = vbox(self, margins=(16, 14, 16, 14), spacing=8)

        head = hbox(spacing=8)
        self._head = label(f"{LANG.m(STR, 'member')} {index + 1}", "H2")
        head.addWidget(self._head)
        head.addStretch(1)
        self._rm = chip("", checkable=False)
        self._rm.clicked.connect(lambda: self.removed.emit(self))
        head.addWidget(self._rm)
        lay.addLayout(head)

        # 공명자
        self._reso = QComboBox()
        for r in self._resos:
            self._reso.addItem(LANG.name(r), str(r["id"]))
        self._reso.currentIndexChanged.connect(self._on_reso)
        self._reso_row = _labeled("", self._reso)
        lay.addWidget(self._reso_row)

        # 레벨 / 사슬 / 풀업
        self._lvl = _spin(1, 90, 90)
        self._seq = QComboBox()
        for i in range(7):
            self._seq.addItem(f"S{i}", i)
        self._full = QCheckBox()
        r1 = hbox(spacing=8)
        self._lvl_lb = label("", "Muted")
        self._seq_lb = label("", "Muted")
        r1.addWidget(self._lvl_lb)
        r1.addWidget(self._lvl)
        r1.addWidget(self._seq_lb)
        r1.addWidget(self._seq)
        self._full_lb = label("", "Muted")
        r1.addWidget(self._full_lb)
        r1.addWidget(self._full)
        r1.addStretch(1)
        lay.addLayout(r1)

        # 무기 / 무기레벨 / 정제
        self._weap = QComboBox()
        self._wlv = _spin(1, 90, 90)
        self._rank = QComboBox()
        for i in range(1, 6):
            self._rank.addItem(f"R{i}", i)
        r2 = hbox(spacing=8)
        self._weap_lb = label("", "Muted")
        r2.addWidget(self._weap_lb)
        r2.addWidget(self._weap, 1)
        self._wlv_lb = label("", "Muted")
        r2.addWidget(self._wlv_lb)
        r2.addWidget(self._wlv)
        self._rank_lb = label("", "Muted")
        r2.addWidget(self._rank_lb)
        r2.addWidget(self._rank)
        lay.addLayout(r2)

        # 스킬별 개별 레벨(damage 있는 스킬만) — _on_reso 에서 재구성
        self._skill_lb = label("", "Muted")
        lay.addWidget(self._skill_lb)
        self._skill_grid = QGridLayout()
        self._skill_grid.setContentsMargins(0, 0, 0, 0)
        self._skill_grid.setHorizontalSpacing(6)
        self._skill_grid.setVerticalSpacing(4)
        self._skill_spins: list[tuple[int, QSpinBox]] = []  # (skill_index, spin)
        lay.addLayout(self._skill_grid)

        lay.addWidget(hsep())

        # 소나타 + 메인옵션
        self._sonata = QComboBox()
        for s in self._sonatas:
            self._sonata.addItem(LANG.field(s, "name"), s.get("name_ko"))
        self._sonata_row = _labeled("", self._sonata)
        lay.addWidget(self._sonata_row)

        self._mains_lb = label("", "Muted")
        lay.addWidget(self._mains_lb)
        # 슬롯 5개: [에코 콤보 + 메인스탯 콤보] 세로 묶음 셀, 3열 그리드
        self._echo_combos: list[QComboBox] = []
        self._main_combos: list[QComboBox] = []
        slots_grid = QGridLayout()
        slots_grid.setContentsMargins(0, 0, 0, 0)
        slots_grid.setHorizontalSpacing(6)
        slots_grid.setVerticalSpacing(6)
        for i, cost in enumerate(_SLOT_COSTS):
            ecb = QComboBox()
            # sizeHint 가 최장 에코명 기준으로 커져 가로 오버플로 → 최소 길이 기준으로 축소
            ecb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            ecb.setMinimumContentsLength(6)
            ecb.setMinimumWidth(0)
            for e in self._echoes:
                if int(e["cost"]) == cost:
                    ecb.addItem(LANG.name(e), str(e["id"]))
            self._echo_combos.append(ecb)
            cb = QComboBox()
            cb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            cb.setMinimumContentsLength(6)
            cb.setMinimumWidth(0)
            for opt in calc.echo_main_options(self._gc, cost):
                cb.addItem(f"{LANG.stat(opt['key'])}·C{cost}", opt["key"])
            self._main_combos.append(cb)
            cell = QWidget()
            clay = vbox(cell, spacing=2)
            clay.addWidget(label(f"C{cost}", "Faint"))
            clay.addWidget(ecb)
            clay.addWidget(cb)
            slots_grid.addWidget(cell, i // 3, i % 3)
        for c in range(3):
            slots_grid.setColumnStretch(c, 1)
        lay.addLayout(slots_grid)
        # 소나타 = 세트 일괄 적용 프리셋(이후 슬롯별 오버라이드 가능)
        self._sonata.currentIndexChanged.connect(self._apply_sonata)
        self._apply_sonata()

        # 축약 서브옵션
        self._subs_lb = label("", "Muted")
        lay.addWidget(self._subs_lb)
        self._sub_spins: dict[str, QDoubleSpinBox] = {}
        subs_row = hbox(spacing=8)
        for key, pct in _SUB_KEYS:
            sp = _spin(0, 9999, 0, decimals=1, suffix="%" if pct else "")
            self._sub_spins[key] = sp
            cell = QWidget()
            cl = vbox(cell, spacing=2)
            cl.addWidget(label(LANG.stat(key), "Faint"))
            cl.addWidget(sp)
            subs_row.addWidget(cell)
        subs_row.addStretch(1)
        lay.addLayout(subs_row)

        self._on_reso()
        self.retranslate()

    # --- 무기 목록을 공명자 무기 타입에 맞춰 필터 ---------------------------
    def _on_reso(self) -> None:
        rid = self._reso.currentData()
        reso = next((r for r in self._resos if str(r["id"]) == rid), None)
        wt = reso.get("weapon_type") if reso else None
        self._weap.clear()
        for w in self._weapons:
            if wt is None or w.get("weapon_type") == wt:
                self._weap.addItem(LANG.name(w), str(w["id"]))
        self._rebuild_skills(reso)
        # 소나타 메인 기본값: C4=크리 피해, C3=속성 피해%, C1=공격력%
        if reso:
            self._apply_default_mains(reso.get("element"))
        self.resoChanged.emit()

    def _rebuild_skills(self, reso: dict | None) -> None:
        """damage 있는 스킬만 개별 레벨 스핀(2열). 라벨은 엔진 규약 SkillType 그대로."""
        clear_layout(self._skill_grid)
        self._skill_spins = []
        for idx, sk in enumerate((reso.get("skills") or []) if reso else []):
            if not sk.get("damage"):
                continue
            sp = _spin(1, 10, 10)
            cell = QWidget()
            clay = hbox(cell, spacing=6)
            clay.addWidget(label(sk.get("SkillType") or "", "Faint"))
            clay.addStretch(1)
            clay.addWidget(sp)
            pos = len(self._skill_spins)
            self._skill_spins.append((idx, sp))
            self._skill_grid.addWidget(cell, pos // 2, pos % 2)

    def _apply_sonata(self) -> None:
        """소나타 일괄 적용: 각 슬롯을 세트 소속 + cost 일치 첫 에코로 설정."""
        set_name = self._sonata.currentData()
        for slot, cost in enumerate(_SLOT_COSTS):
            e = next((e for e in self._echoes
                      if int(e["cost"]) == cost and set_name in (e.get("sonata") or [])), None)
            if e is None:
                continue
            i = self._echo_combos[slot].findData(str(e["id"]))
            if i >= 0:
                self._echo_combos[slot].setCurrentIndex(i)

    def _apply_default_mains(self, element: str | None) -> None:
        edmg = ELEMENT_DMG_KEY.get(element or "")
        defaults = ["critDmg", edmg or "atkPct", edmg or "atkPct", "atkPct", "atkPct"]
        for cb, want in zip(self._main_combos, defaults):
            i = cb.findData(want)
            cb.setCurrentIndex(i if i >= 0 else 0)

    # --- build ------------------------------------------------------------
    def build(self):
        rid = self._reso.currentData()
        reso = next((r for r in self._resos if str(r["id"]) == rid), None)
        skills = (reso.get("skills") or []) if reso else []

        subs = [
            engine.SubIn(key=key, value=sp.value())
            for key, sp in self._sub_spins.items()
            if sp.value()
        ]
        echoes = []
        for slot, cost in enumerate(_SLOT_COSTS):
            echoes.append(engine.EchoIn(
                echo_id=self._echo_combos[slot].currentData() or "0",
                cost=cost,
                main=self._main_combos[slot].currentData(),
                subs=subs if slot == 0 else [],  # 배치 무관 → 첫 슬롯에 합산
            ))
        # 기본 10 + 노출된 스핀 값으로 덮기(damage 없는 스킬은 10 고정)
        skill_levels = {i: 10 for i in range(len(skills))}
        for idx, sp in self._skill_spins:
            skill_levels[idx] = sp.value()
        return engine.MemberIn(
            reso_id=rid,
            level=self._lvl.value(),
            weapon_id=self._weap.currentData(),
            weapon_level=self._wlv.value(),
            weapon_rank=self._rank.currentData(),
            echoes=echoes,
            skill_levels=skill_levels,
            full_uptime=self._full.isChecked(),
            sequence=self._seq.currentData(),
        )

    def set_index(self, index: int) -> None:
        self._head.setText(f"{LANG.m(STR, 'member')} {index + 1}")

    def retranslate(self) -> None:
        self._rm.setText(LANG.m(STR, "remove"))
        self._lvl_lb.setText(LANG.m(STR, "level"))
        self._seq_lb.setText(LANG.m(STR, "sequence"))
        self._full_lb.setText(LANG.m(STR, "full_uptime"))
        self._weap_lb.setText(LANG.m(STR, "weapon"))
        self._wlv_lb.setText(LANG.m(STR, "wlv"))
        self._rank_lb.setText(LANG.m(STR, "rank"))
        self._skill_lb.setText(LANG.m(STR, "skill"))
        self._reso_row.layout().itemAt(0).widget().setText(LANG.t("codex_resonators"))
        self._sonata_row.layout().itemAt(0).widget().setText(LANG.m(STR, "sonata"))
        self._mains_lb.setText(LANG.m(STR, "mains"))
        self._subs_lb.setText(LANG.m(STR, "subs"))


class _CalcWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, request) -> None:
        super().__init__()
        self._req = request

    def run(self) -> None:
        try:
            self.done.emit(engine.calculate(self._req))
        except Exception as exc:  # noqa: BLE001 — surface to UI
            self.failed.emit(str(exc))


def _bar(frac: float) -> QWidget:
    """가로 지분 막대(accent 채움)."""
    frac = max(0.0, min(1.0, frac))
    w = QWidget()
    w.setFixedHeight(8)
    lay = hbox(w, margins=(0, 0, 0, 0), spacing=0)
    fill = QFrame()
    fill.setStyleSheet(f"background:{THEME.palette['accent']};border-radius:4px;")
    empty = QFrame()
    empty.setStyleSheet(f"background:{THEME.palette['surface2']};border-radius:4px;")
    lay.addWidget(fill, max(1, round(frac * 1000)))
    lay.addWidget(empty, max(1, round((1 - frac) * 1000)))
    return w


class TeamsTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._reso_map = {str(r["id"]): r for r in engine.resonators()}
        self._members: list[_MemberEditor] = []
        self._worker: _CalcWorker | None = None

        root = hbox(self, margins=(16, 16, 16, 12), spacing=16)

        # 왼쪽: 편집(스크롤)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(560)
        left_host = QWidget()
        self._left = vbox(left_host, margins=(0, 0, 8, 0), spacing=12)

        # 전투 조건
        cond = card()
        cl = vbox(cond, margins=(16, 14, 16, 14), spacing=8)
        self._cond_lb = label("", "H2")
        cl.addWidget(self._cond_lb)
        self._enemy_lv = _spin(1, 200, 90)
        self._enemy_res = _spin(-100, 100, 20, decimals=1, suffix="%")
        self._res_shred = _spin(0, 100, 0, decimals=1, suffix="%")
        self._def_reduce = _spin(0, 100, 0, decimals=1, suffix="%")
        self._boost = _spin(0, 500, 0, decimals=1, suffix="%")
        self._party_shred = _spin(0, 100, 0, decimals=1, suffix="%")
        self._cond_rows = [
            ("enemy_level", self._enemy_lv), ("enemy_res", self._enemy_res),
            ("res_shred", self._res_shred), ("def_reduce", self._def_reduce),
            ("boost", self._boost), ("party_shred", self._party_shred),
        ]
        grid = hbox(spacing=8)
        self._cond_cells: list[tuple[str, QWidget]] = []
        col = vbox(spacing=6)
        for i, (key, w) in enumerate(self._cond_rows):
            cell = _labeled("", w)
            self._cond_cells.append((key, cell))
            col.addWidget(cell)
            if i == 2:
                grid.addLayout(col)
                col = vbox(spacing=6)
        grid.addLayout(col)
        cl.addLayout(grid)
        self._left.addWidget(cond)

        self._members_host = QWidget()
        self._members_lay = vbox(self._members_host, margins=(0, 0, 0, 0), spacing=12)
        self._left.addWidget(self._members_host)

        btns = hbox(spacing=8)
        self._add_btn = chip("", checkable=False)
        self._add_btn.clicked.connect(self._add_member)
        self._calc_btn = QPushButton()
        self._calc_btn.setObjectName("Accent")
        self._calc_btn.clicked.connect(self._calculate)
        btns.addWidget(self._add_btn)
        btns.addStretch(1)
        btns.addWidget(self._calc_btn)
        self._left.addLayout(btns)
        self._left.addStretch(1)
        left_scroll.setWidget(left_host)
        root.addWidget(left_scroll)

        # 오른쪽: 결과(스크롤)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        res_host = QWidget()
        self._results = vbox(res_host, margins=(0, 0, 0, 0), spacing=10)
        right_scroll.setWidget(res_host)
        root.addWidget(right_scroll, 1)
        self._has_result = False
        self._show_empty()

        self._add_member()
        self.retranslate()

    def _show_empty(self) -> None:
        """결과 없을 때 오른쪽 패널 빈 상태 안내(빈 공백 대신)."""
        self._has_result = False
        clear_layout(self._results)
        box = card()
        bl = vbox(box, margins=(28, 44, 28, 44), spacing=10)
        bl.setAlignment(Qt.AlignCenter)
        glyph = label("🎐", None)
        glyph.setAlignment(Qt.AlignCenter)
        glyph.setStyleSheet("font-size:36px;")
        hint = label(LANG.m(STR, "empty_hint"), "Muted", wrap=True)
        hint.setAlignment(Qt.AlignCenter)
        bl.addWidget(glyph)
        bl.addWidget(hint)
        self._results.addWidget(box)
        self._results.addStretch(1)

    # --- 멤버 관리 ---------------------------------------------------------
    def _add_member(self) -> None:
        if len(self._members) >= 3:
            return
        m = _MemberEditor(len(self._members))
        m.removed.connect(self._remove_member)
        m.resoChanged.connect(self._sync_reso_locks)
        self._members.append(m)
        self._members_lay.addWidget(m)
        # 새 멤버는 아직 안 뽑힌 첫 공명자로(중복 방지)
        taken = {x._reso.currentData() for x in self._members if x is not m}
        for i in range(m._reso.count()):
            if m._reso.itemData(i) not in taken:
                m._reso.setCurrentIndex(i)
                break
        self._reindex()

    def _remove_member(self, m: _MemberEditor) -> None:
        if m not in self._members:
            return
        self._members.remove(m)
        m.setParent(None)
        m.deleteLater()
        self._reindex()

    def _reindex(self) -> None:
        for i, m in enumerate(self._members):
            m.set_index(i)
        self._add_btn.setVisible(len(self._members) < 3)  # 3명 차면 추가 버튼 숨김
        self._sync_reso_locks()

    def _sync_reso_locks(self) -> None:
        """다른 멤버가 이미 고른 공명자는 콤보 아이템 비활성(자기 선택은 유지)."""
        taken = {m._reso.currentData() for m in self._members}
        for m in self._members:
            cb = m._reso
            own = cb.currentData()
            model = cb.model()  # QComboBox 기본 = QStandardItemModel
            for i in range(cb.count()):
                rid = cb.itemData(i)
                model.item(i).setEnabled(rid == own or rid not in taken)

    # --- 계산 --------------------------------------------------------------
    def _opts(self):
        return engine.OptsIn(
            enemy_level=self._enemy_lv.value(),
            enemy_res=self._enemy_res.value() / 100,
            res_shred=self._res_shred.value() / 100,
            def_reduce=self._def_reduce.value() / 100,
            boost=self._boost.value() / 100,
        )

    def _calculate(self) -> None:
        if not self._members or (self._worker and self._worker.isRunning()):
            return
        req = engine.TeamCalcRequest(
            members=[m.build() for m in self._members],
            opts=self._opts(),
            party_def_shred=self._party_shred.value() / 100,
        )
        self._calc_btn.setEnabled(False)
        self._worker = _CalcWorker(req)
        self._worker.done.connect(self._on_result)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_fail(self, msg: str) -> None:
        self._calc_btn.setEnabled(True)
        self._has_result = False
        clear_layout(self._results)
        self._results.addWidget(label(f"⚠ {msg}", "Muted", wrap=True))
        self._results.addStretch(1)

    def _on_result(self, resp) -> None:
        self._calc_btn.setEnabled(True)
        self._has_result = True
        clear_layout(self._results)

        total = resp.team_total or 0
        head = card("Card2")
        hl = vbox(head, margins=(16, 14, 16, 14), spacing=2)
        hl.addWidget(label(LANG.m(STR, "team_total"), "Muted"))
        hl.addWidget(label(f"{round(total):,}", "H1"))
        if self._save_history(resp):
            hl.addWidget(label(LANG.m(STR, "saved_history"), "Faint"))
        self._results.addWidget(head)

        for m in sorted(resp.members, key=lambda x: x.total, reverse=True):
            self._results.addWidget(self._member_result(m, total))
        self._results.addStretch(1)

    def _save_history(self, resp) -> bool:
        """계산 결과를 기록 탭(로컬 JSON 스토어)에 자동 저장."""
        try:
            import uuid
            from datetime import datetime

            total = resp.team_total or 0
            members = sorted(resp.members, key=lambda x: x.total, reverse=True)
            names, picks = [], []
            for m in members:
                reso = self._reso_map.get(str(m.reso_id))
                names.append(LANG.name(reso) if reso else str(m.reso_id))
                share = (m.total / total * 100) if total else 0
                picks.append(engine.TeamPick(
                    resonator_id=str(m.reso_id),
                    reason=f"딜 {round(m.total):,} · 지분 {share:.1f}%",
                ))
            engine.ai_save(engine.AiRecommendationRecord(
                id=uuid.uuid4().hex,
                created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                profile=engine.AiProfile(),
                conversation=[],
                recommendation=engine.Recommendation(
                    summary=f"파티 딜 계산 — 팀 총딜 {round(total):,}",
                    team=picks,
                ),
                title=f"파티 딜 {round(total):,} · {', '.join(names)}",
            ))
            return True
        except Exception:  # noqa: BLE001 — 기록 실패해도 결과 표시는 계속
            return False

    def _member_result(self, m, team_total: float) -> QWidget:
        box = card()
        lay = vbox(box, margins=(16, 14, 16, 14), spacing=6)
        reso = self._reso_map.get(str(m.reso_id))
        name = LANG.name(reso) if reso else (m.name or str(m.reso_id))
        share = (m.total / team_total) if team_total else 0

        top = hbox(spacing=8)
        seq = f"  S{m.sequence}" if m.sequence else ""
        top.addWidget(label(f"{name}{seq}", "H2"))
        top.addStretch(1)
        top.addWidget(label(f"{round(m.total):,}  ·  {share * 100:.1f}%", "Gold"))
        lay.addLayout(top)
        lay.addWidget(_bar(share))

        # 스킬 딜
        lay.addWidget(label(LANG.m(STR, "skills"), "Faint"))
        for s in sorted(m.skills, key=lambda x: x.dmg, reverse=True):
            if s.dmg <= 0:
                continue
            row = hbox(spacing=8)
            row.addWidget(label(f"{s.name} · {LANG.skill_type(s.type)}", "Muted"))
            row.addStretch(1)
            row.addWidget(label(f"{round(s.dmg):,}", "Muted"))
            lay.addLayout(row)

        # 상황부(총딜 제외)
        sit = []
        if m.anomaly_dmg:
            sit.append(f"{LANG.m(STR, 'anomaly')}({m.anomaly_type or ''}) {round(m.anomaly_dmg):,}")
        if m.tune_break_dmg:
            sit.append(f"{LANG.m(STR, 'tune_break')} {round(m.tune_break_dmg):,}")
        if sit:
            lay.addWidget(hsep())
            lay.addWidget(label(LANG.m(STR, "situational"), "Faint"))
            lay.addWidget(label("  ·  ".join(sit), "Muted", wrap=True))

        # 적용 팀 버프
        if m.applied_team_buffs:
            lay.addWidget(label(
                f"{LANG.m(STR, 'team_buffs')}: " + ", ".join(m.applied_team_buffs), "Faint", wrap=True))
        for note in (m.team_notes or []):
            lay.addWidget(label(f"• {note}", "Faint", wrap=True))
        return box

    def retranslate(self) -> None:
        self._cond_lb.setText(LANG.m(STR, "conditions"))
        for key, cell in self._cond_cells:
            cell.layout().itemAt(0).widget().setText(LANG.m(STR, key))
        self._add_btn.setText(LANG.m(STR, "add_member"))
        self._calc_btn.setText(LANG.m(STR, "calculate"))
        for m in self._members:
            m.retranslate()
        if not self._has_result:
            self._show_empty()


if __name__ == "__main__":  # smoke: build 2 members + real engine calc + all langs
    import os
    import sys

    import tempfile

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault("LOCAL_DATA_DIR", tempfile.mkdtemp())  # dev 스토어 오염 방지(_save_history)
    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")
    from PySide6.QtWidgets import QApplication

    app = QApplication([])
    tab = TeamsTab()
    tab._add_member()  # 2 members
    m1, m2 = tab._members
    assert m1._reso.currentData() != m2._reso.currentData(), "새 멤버는 다른 공명자로 자동 배정"
    j = m2._reso.findData(m1._reso.currentData())
    assert not m2._reso.model().item(j).isEnabled(), "멤버1 선택이 멤버2 콤보에서 disabled"
    assert m1._skill_spins, "스킬별 레벨 스핀 존재"
    assert len(m1._echo_combos) == 5 and all(c.count() for c in m1._echo_combos), "에코 콤보 5개"
    for code in ("ko", "en", "ja", "zhHans"):
        LANG.set(code)
        tab.retranslate()
    LANG.set("ko")  # 저장 타이틀이 마지막 언어(zh)로 남지 않도록 복귀
    # 실엔진 계산 동기 실행(스레드 안 거치고 직접)
    req = engine.TeamCalcRequest(
        members=[m.build() for m in tab._members],
        opts=tab._opts(),
        party_def_shred=0.0,
    )
    resp = engine.calculate(req)
    assert resp.team_total > 0, "team_total should be positive"
    assert len(resp.members) == 2
    tab._on_result(resp)
    app.processEvents()
    print("teams ok", round(resp.team_total))
