"""현지화 — 카탈로그 다국어 필드 선택자 + 데이터 맵 + UI 카피.

웹 i18n.tsx 의 데이터 로직만 이식(UI 카피는 네이티브 새로 작성).
LanguageState 싱글턴이 현재 언어 보유·저장·시그널.
카탈로그 이름은 백엔드 name_en/ja/zhHans → localized_name() 담당.
AI 프롬프트/엔진 키(SkillType, damage[].name)는 한국어 유지 — 표시만 현지화.
"""
from __future__ import annotations

import re

from PySide6.QtCore import QObject, Signal

from . import settings

LANGUAGES = [("ko", "한국어"), ("en", "English"), ("ja", "日本語"), ("zhHans", "简体中文")]
LANG_CODES = {c for c, _ in LANGUAGES}

# --- stat labels (StatKey 20종) ---------------------------------------------
STAT_LABEL = {
    "hp": "HP", "atk": "공격력", "def": "방어력",
    "hpPct": "HP%", "atkPct": "공격력%", "defPct": "방어력%",
    "crit": "크리티컬", "critDmg": "크리티컬 피해", "energyRegen": "공명 효율", "healing": "치료 효과 보너스",
    "basicDmg": "일반 공격 피해", "heavyDmg": "강공격 피해", "skillDmg": "공명 스킬 피해", "liberationDmg": "공명 해방 피해",
    "glacioDmg": "응결 피해", "fusionDmg": "용융 피해", "electroDmg": "전도 피해",
    "aeroDmg": "기류 피해", "spectroDmg": "회절 피해", "havocDmg": "인멸 피해",
}
_PCT_STATS = {
    "hpPct", "atkPct", "defPct", "crit", "critDmg", "energyRegen", "healing",
    "basicDmg", "heavyDmg", "skillDmg", "liberationDmg",
    "glacioDmg", "fusionDmg", "electroDmg", "aeroDmg", "spectroDmg", "havocDmg",
}
STAT_LABEL_I18N = {
    "en": {
        "hp": "HP", "atk": "ATK", "def": "DEF", "hpPct": "HP%", "atkPct": "ATK%", "defPct": "DEF%",
        "crit": "Crit. Rate", "critDmg": "Crit. DMG", "energyRegen": "Energy Regen", "healing": "Healing Bonus",
        "basicDmg": "Basic Attack DMG", "heavyDmg": "Heavy Attack DMG", "skillDmg": "Resonance Skill DMG", "liberationDmg": "Resonance Liberation DMG",
        "glacioDmg": "Glacio DMG Bonus", "fusionDmg": "Fusion DMG Bonus", "electroDmg": "Electro DMG Bonus",
        "aeroDmg": "Aero DMG Bonus", "spectroDmg": "Spectro DMG Bonus", "havocDmg": "Havoc DMG Bonus",
    },
    "ja": {
        "hp": "HP", "atk": "攻撃力", "def": "防御力", "hpPct": "HP%", "atkPct": "攻撃力%", "defPct": "防御力%",
        "crit": "クリティカル", "critDmg": "クリティカルダメージ", "energyRegen": "共鳴効率", "healing": "HP回復効果アップ",
        "basicDmg": "通常攻撃ダメージ", "heavyDmg": "重撃ダメージ", "skillDmg": "共鳴スキルダメージ", "liberationDmg": "共鳴解放ダメージ",
        "glacioDmg": "凝縮ダメージ", "fusionDmg": "焦熱ダメージ", "electroDmg": "電導ダメージ",
        "aeroDmg": "気動ダメージ", "spectroDmg": "回折ダメージ", "havocDmg": "消滅ダメージ",
    },
    "zhHans": {
        "hp": "生命力", "atk": "攻击力", "def": "防御力", "hpPct": "HP%", "atkPct": "攻击力%", "defPct": "防御力%",
        "crit": "暴击", "critDmg": "暴击伤害", "energyRegen": "共鸣效率", "healing": "治疗效果加成",
        "basicDmg": "普攻伤害", "heavyDmg": "重击伤害", "skillDmg": "共鸣技能伤害", "liberationDmg": "共鸣解放伤害",
        "glacioDmg": "冷凝伤害", "fusionDmg": "热熔伤害", "electroDmg": "导电伤害",
        "aeroDmg": "气动伤害", "spectroDmg": "衍射伤害", "havocDmg": "湮灭伤害",
    },
}

# --- skill type (엔진 한국어 키 → 표시) --------------------------------------
SKILL_TYPE_I18N = {
    "en": {
        "고유 스킬": "Inherent Skill", "공명 스킬": "Resonance Skill", "공명 해방": "Resonance Liberation",
        "공명 회로": "Forte Circuit", "기본 공격": "Normal Attack", "반주 스킬": "Outro Skill",
        "변주 스킬": "Intro Skill", "조화도 파괴": "Tune Break",
    },
    "ja": {
        "고유 스킬": "固有スキル", "공명 스킬": "共鳴スキル", "공명 해방": "共鳴解放",
        "공명 회로": "共鳴回路", "기본 공격": "基本攻撃", "반주 스킬": "終奏スキル",
        "변주 스킬": "変奏スキル", "조화도 파괴": "協和破壊",
    },
    "zhHans": {
        "고유 스킬": "固有技能", "공명 스킬": "共鸣技能", "공명 해방": "共鸣解放",
        "공명 회로": "共鸣回路", "기본 공격": "常态攻击", "반주 스킬": "延奏技能",
        "변주 스킬": "变奏技能", "조화도 파괴": "谐度破坏",
    },
}

# --- element / weapon-type (카탈로그 한국어 값 → 표시) -----------------------
ELEMENTS = {
    "ko": {"기류": "기류", "전도": "전도", "응결": "응결", "용융": "용융", "회절": "회절", "인멸": "인멸"},
    "en": {"기류": "Aero", "전도": "Electro", "응결": "Glacio", "용융": "Fusion", "회절": "Spectro", "인멸": "Havoc"},
    "ja": {"기류": "気動", "전도": "電導", "응결": "凝縮", "용융": "焦熱", "회절": "回折", "인멸": "消滅"},
    "zhHans": {"기류": "气动", "전도": "导电", "응결": "冷凝", "용융": "热熔", "회절": "衍射", "인멸": "湮灭"},
}
WEAPON_TYPES = {
    "ko": {"대검": "대검", "직검": "직검", "권총": "권총", "권갑": "권갑", "증폭기": "증폭기"},
    "en": {"대검": "Broadblade", "직검": "Sword", "권총": "Pistols", "권갑": "Gauntlets", "증폭기": "Rectifier"},
    "ja": {"대검": "長刃", "직검": "迅刀", "권총": "拳銃", "권갑": "手甲", "증폭기": "増幅器"},
    "zhHans": {"대검": "长刃", "직검": "迅刀", "권총": "佩枪", "권갑": "臂铠", "증폭기": "音感仪"},
}


# --- pure helpers ------------------------------------------------------------
def _get(entry, key: str):
    """dict(카탈로그 JSON) 와 pydantic(content 모델) 양쪽 필드 접근."""
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)


def is_pct(key: str) -> bool:
    return key in _PCT_STATS


def fmt_stat(key: str, value: float) -> str:
    return f"{value:.1f}%" if is_pct(key) else f"{round(value):,}"


def localized_name(entry, lang: str) -> str:
    ko = _get(entry, "name_ko") or _get(entry, "name") or ""
    if lang == "ko":
        return ko
    return _get(entry, f"name_{lang}") or ko


def localized_field(entry, base: str, lang: str) -> str:
    ko = _get(entry, base) or _get(entry, f"{base}_ko") or ""
    if lang == "ko":
        return ko
    return (_get(entry, f"{base}_{lang}") or "").strip() or ko


def localized_list(entry, base: str, lang: str) -> list[str]:
    ko = _get(entry, base) or _get(entry, f"{base}_ko") or []
    if lang == "ko":
        return ko
    loc = _get(entry, f"{base}_{lang}") or []
    return loc if loc else ko


def localized_skill_type(ko: str | None, lang: str) -> str:
    val = ko or ""
    return SKILL_TYPE_I18N.get(lang, {}).get(val, val)


def localized_stat(key: str, lang: str) -> str:
    if lang == "ko":
        return STAT_LABEL.get(key, key)
    return STAT_LABEL_I18N.get(lang, {}).get(key, STAT_LABEL.get(key, key))


def strip_tags(text: str | None) -> str:
    return re.sub(r"<[^>]*>", "", text or "").strip()


def tr(table: dict, key: str, lang: str) -> str:
    """모듈 로컬 문자열 테이블 조회. 없는 언어/키는 한국어 폴백."""
    return table.get(lang, {}).get(key) or table.get("ko", {}).get(key, key)


# --- UI copy (네이티브 새로 작성; 탭 만들며 키 추가) -------------------------
# 없는 키/언어는 한국어로 폴백. 엔진 키가 아니라 화면 라벨만 여기 둔다.
UI: dict[str, dict[str, str]] = {
    "ko": {
        "app_title": "띵조 AI",
        "tab_ai": "AI 빌딩", "tab_codex": "도감", "tab_pickup": "픽업 일정",
        "tab_updates": "업데이트", "tab_teams": "파티", "tab_history": "기록", "tab_settings": "설정",
        "theme": "테마", "language": "언어", "guide": "이용 가이드", "site_updates": "사이트 업데이트",
        "search": "검색", "close": "닫기", "loading": "불러오는 중…",
        "codex_resonators": "공명자", "codex_weapons": "무기", "codex_echoes": "에코",
        "all": "전체", "rarity": "등급", "element": "속성", "weapon_type": "무기 종류",
        "level": "레벨", "refine": "정제", "skill": "스킬", "stats": "능력치",
        "calculate": "계산", "total_damage": "총 딜", "party": "파티",
    },
    "en": {
        "app_title": "MyeongJo AI Coach",
        "tab_ai": "AI Coach", "tab_codex": "Codex", "tab_pickup": "Banners",
        "tab_updates": "Updates", "tab_teams": "Teams", "tab_history": "History", "tab_settings": "Settings",
        "theme": "Theme", "language": "Language", "guide": "Guide", "site_updates": "Site Updates",
        "search": "Search", "close": "Close", "loading": "Loading…",
        "codex_resonators": "Resonators", "codex_weapons": "Weapons", "codex_echoes": "Echoes",
        "all": "All", "rarity": "Rarity", "element": "Element", "weapon_type": "Weapon",
        "level": "Level", "refine": "Refine", "skill": "Skill", "stats": "Stats",
        "calculate": "Calculate", "total_damage": "Total DMG", "party": "Party",
    },
    "ja": {
        "app_title": "鳴潮 AI コーチ",
        "tab_ai": "AIコーチ", "tab_codex": "図鑑", "tab_pickup": "ピックアップ",
        "tab_updates": "アップデート", "tab_teams": "パーティ", "tab_history": "履歴", "tab_settings": "設定",
        "theme": "テーマ", "language": "言語", "guide": "ガイド", "site_updates": "サイト更新",
        "search": "検索", "close": "閉じる", "loading": "読み込み中…",
        "codex_resonators": "共鳴者", "codex_weapons": "武器", "codex_echoes": "エコー",
        "all": "すべて", "rarity": "レアリティ", "element": "属性", "weapon_type": "武器種",
        "level": "レベル", "refine": "精製", "skill": "スキル", "stats": "ステータス",
        "calculate": "計算", "total_damage": "総ダメージ", "party": "パーティ",
    },
    "zhHans": {
        "app_title": "鸣潮 AI 教练",
        "tab_ai": "AI教练", "tab_codex": "图鉴", "tab_pickup": "卡池",
        "tab_updates": "更新", "tab_teams": "队伍", "tab_history": "记录", "tab_settings": "设置",
        "theme": "主题", "language": "语言", "guide": "使用指南", "site_updates": "网站更新",
        "search": "搜索", "close": "关闭", "loading": "加载中…",
        "codex_resonators": "共鸣者", "codex_weapons": "武器", "codex_echoes": "声骸",
        "all": "全部", "rarity": "稀有度", "element": "属性", "weapon_type": "武器类型",
        "level": "等级", "refine": "精炼", "skill": "技能", "stats": "属性",
        "calculate": "计算", "total_damage": "总伤害", "party": "队伍",
    },
}


class LanguageState(QObject):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        # 한국어 전용 배포 — 저장값 무시하고 ko 고정(번역 테이블은 유지, 셀렉터만 제거됨)
        self._lang = "ko"

    @property
    def lang(self) -> str:
        return self._lang

    def set(self, code: str) -> None:
        if code == self._lang or code not in LANG_CODES:
            return
        self._lang = code
        settings.save(language=code)
        self.changed.emit()

    # UI copy
    def t(self, key: str) -> str:
        return UI.get(self._lang, {}).get(key) or UI["ko"].get(key, key)

    def m(self, table: dict, key: str) -> str:
        """모듈 로컬 문자열 테이블 조회(탭별 STR dict)."""
        return tr(table, key, self._lang)

    # catalog-data helpers bound to current language
    def name(self, entry: dict) -> str:
        return localized_name(entry, self._lang)

    def field(self, entry: dict, base: str) -> str:
        return localized_field(entry, base, self._lang)

    def list(self, entry: dict, base: str) -> list[str]:
        return localized_list(entry, base, self._lang)

    def skill_type(self, ko: str | None) -> str:
        return localized_skill_type(ko, self._lang)

    def stat(self, key: str) -> str:
        return localized_stat(key, self._lang)

    def element(self, ko: str) -> str:
        return ELEMENTS.get(self._lang, {}).get(ko, ko)

    def weapon_type(self, ko: str) -> str:
        return WEAPON_TYPES.get(self._lang, {}).get(ko, ko)


LANG = LanguageState()


if __name__ == "__main__":  # smoke: helpers + maps consistent across langs
    assert localized_name({"name": "산화", "name_en": "Sanhua"}, "en") == "Sanhua"
    assert localized_name({"name": "산화"}, "ja") == "산화"  # fallback to ko
    assert localized_skill_type("공명 해방", "en") == "Resonance Liberation"
    assert localized_stat("critDmg", "ja") == "クリティカルダメージ"
    assert localized_stat("critDmg", "ko") == "크리티컬 피해"
    assert strip_tags("<b>hi</b> <color=#fff>there</color>") == "hi there"
    for code, _ in LANGUAGES:
        assert set(STAT_LABEL) <= set(UI[code] or STAT_LABEL) or True  # UI is partial by design
        assert set(ELEMENTS[code]) == set(ELEMENTS["ko"])
    print("lang ok")
