from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["main_dps", "sub_dps", "support", "healer"]
Grade = Literal["excellent", "keep", "upgrade", "hold", "replace", "discard"]
ScreenType = Literal["character_status", "echo_detail", "weapon_detail", "inventory", "team", "unknown"]


class StatBlock(BaseModel):
    hp: str | None = None
    atk: str | None = None
    defense: str | None = None
    crit_rate: str | None = None
    crit_dmg: str | None = None
    energy_regen: str | None = None
    element_dmg_bonus: str | None = None
    healing_bonus: str | None = None


class SubStat(BaseModel):
    name: str | None = None
    value: str | None = None


class EchoItem(BaseModel):
    name: str | None = None
    slot: str | None = None
    set_name: str | None = None
    cost: int | None = None
    level: int | None = None
    main_stat: str | None = None
    sub_stats: list[SubStat] = Field(default_factory=list)


class WeaponState(BaseModel):
    name: str | None = None
    level: int | None = None
    rank: int | None = None
    main_stat: str | None = None


class CharacterSnapshot(BaseModel):
    character_name: str | None = None
    character_level: int | None = None
    role: Role | None = None
    weapon: WeaponState | None = None
    stats: StatBlock = Field(default_factory=StatBlock)
    echoes: list[EchoItem] = Field(default_factory=list)
    raw_text: str = ""


class VisionExtractionResult(BaseModel):
    screen_type: ScreenType = "unknown"
    snapshot: CharacterSnapshot = Field(default_factory=CharacterSnapshot)
    uncertain_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None
    raw_model_output: str | None = None


class BuildRule(BaseModel):
    character_name: str
    role: Role
    recommended_sets: list[str]
    priority_stats: list[str]
    useful_sub_stats: list[str]
    bad_sub_stats: list[str]
    recommended_weapons: list[str] = Field(default_factory=list)
    notes: str | None = None
    source_links: list[str] = Field(default_factory=list)
    game_version: str | None = None


class PickupBannerCharacter(BaseModel):
    name_ko: str
    avatar: str | None = None
    # Linked wuwa_resonator (game) id when the pickup name matches a resonator;
    # lets the frontend link the pickup icon to codex detail. None for characters
    # not in the dataset (e.g. brand-new units).
    catalog_id: int | None = None


class PickupBannerWeapon(BaseModel):
    name_ko: str
    icon: str | None = None
    rarity: int | None = None
    weapon_type: str | None = None


class PickupBanner(BaseModel):
    id: str
    version: str
    phase: int | None = None
    banner_name: str | None = None
    is_rerun: bool = False
    is_collab: bool = False
    characters: list[PickupBannerCharacter] = Field(default_factory=list)
    weapons: list[PickupBannerWeapon] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None


class PickupScheduleItem(BaseModel):
    id: str
    year: int
    month: int
    day: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    version: str | None = None
    phase: str | None = None
    category: Literal["first_pickup", "rerun_1", "rerun_2", "rerun_3"]
    label_ko: str
    characters: list[str] = Field(default_factory=list)
    appearance_no: int | None = None
    status: str | None = None
    notes_ko: str | None = None
    source_links: list[str] = Field(default_factory=list)


class GameUpdateSummary(BaseModel):
    id: str
    version: str
    title_ko: str
    release_date_kst: str | None = None
    summary_ko: str
    highlights_ko: list[str] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)
    image_url: str | None = None
    # 표시 전용 본문 현지화 (en/ja/zhHans). 없으면 프론트가 _ko로 폴백.
    # 제목(theme명)은 공식 명칭 리스크로 한국어 유지.
    summary_en: str | None = None
    summary_ja: str | None = None
    summary_zhHans: str | None = None
    highlights_en: list[str] = Field(default_factory=list)
    highlights_ja: list[str] = Field(default_factory=list)
    highlights_zhHans: list[str] = Field(default_factory=list)


class SiteUpdateEntry(BaseModel):
    id: str
    date: str
    version: str | None = None
    title_ko: str
    description_ko: str = ""
    # 표시 전용 현지화 (en/ja/zhHans). 없으면 프론트가 _ko로 폴백.
    title_en: str | None = None
    title_ja: str | None = None
    title_zhHans: str | None = None
    description_en: str | None = None
    description_ja: str | None = None
    description_zhHans: str | None = None


class TeamRule(BaseModel):
    name: str
    core_character: str
    recommended_teammates: list[str]
    notes: str | None = None



class AuthUserSyncRequest(BaseModel):
    email: str
    name: str | None = None
    image: str | None = None
    role: Literal["admin", "user"] = "user"
    provider: str = "google"
    provider_account_id: str | None = None


class UserRecord(BaseModel):
    id: str
    email: str
    name: str | None = None
    image: str | None = None
    role: Literal["admin", "user"] = "user"
    created_at: str
    updated_at: str
    last_login_at: str | None = None

class Diagnosis(BaseModel):
    target_type: Literal["echo", "character", "account", "team"]
    target_name: str | None = None
    grade: Grade
    score: int
    reasons: list[str]
    recommended_actions: list[str]


class AnalysisSession(BaseModel):
    id: str
    created_at: str
    image_filename: str | None = None
    extraction: VisionExtractionResult
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    report: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    snapshot: CharacterSnapshot
    fallback_role: Role = "main_dps"


class AnalyzeResponse(BaseModel):
    snapshot: CharacterSnapshot
    diagnoses: list[Diagnosis]
    report: str


# --- AI coach ---------------------------------------------------------------

class AiProfile(BaseModel):
    union_level: int | None = None
    owned_characters: list[str] = Field(default_factory=list)
    desired_characters: list[str] = Field(default_factory=list)
    play_style: str | None = None
    note: str | None = None


class AiMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WeaponPick(BaseModel):
    id: str
    alt_ids: list[str] = Field(default_factory=list)
    reason: str | None = None


class EchoPick(BaseModel):
    sonata_ids: list[str] = Field(default_factory=list)
    main_echo_id: str | None = None
    main_stats: dict[str, str] = Field(default_factory=dict)
    # 추천 추가옵션(추옵) — 우선순위 순 한국어 스탯명, 최대 5개.
    sub_stats: list[str] = Field(default_factory=list)


class TeamPick(BaseModel):
    resonator_id: str
    role: Role | None = None
    reason: str | None = None
    weapon: WeaponPick | None = None
    echo: EchoPick | None = None
    priority: int | None = None


class Recommendation(BaseModel):
    summary: str = ""
    team: list[TeamPick] = Field(default_factory=list)
    upgrade_order: list[str] = Field(default_factory=list)


class AiChatRequest(BaseModel):
    messages: list[AiMessage] = Field(default_factory=list)
    profile: AiProfile = Field(default_factory=AiProfile)


class AiChatResponse(BaseModel):
    reply: str
    recommendation: Recommendation | None = None
    is_final: bool = False


class AiRecommendationRecord(BaseModel):
    id: str
    user_id: str | None = None
    created_at: str
    profile: AiProfile = Field(default_factory=AiProfile)
    conversation: list[AiMessage] = Field(default_factory=list)
    recommendation: Recommendation
    title: str | None = None


class AiRecommendationCreate(BaseModel):
    """확정 저장 요청(id·created_at은 서버가 생성)."""
    user_id: str | None = None
    profile: AiProfile = Field(default_factory=AiProfile)
    conversation: list[AiMessage] = Field(default_factory=list)
    recommendation: Recommendation
    title: str | None = None
