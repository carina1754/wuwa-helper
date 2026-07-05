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


class TeamRule(BaseModel):
    name: str
    core_character: str
    recommended_teammates: list[str]
    notes: str | None = None


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
