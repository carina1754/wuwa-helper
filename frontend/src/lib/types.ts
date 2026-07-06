export type Role = "main_dps" | "sub_dps" | "support" | "healer";
export type Grade = "excellent" | "keep" | "upgrade" | "hold" | "replace" | "discard";
export type ScreenType = "character_status" | "echo_detail" | "weapon_detail" | "inventory" | "team" | "unknown";

export interface StatBlock {
  hp?: string | null;
  atk?: string | null;
  defense?: string | null;
  crit_rate?: string | null;
  crit_dmg?: string | null;
  energy_regen?: string | null;
  element_dmg_bonus?: string | null;
  healing_bonus?: string | null;
}

export interface SubStat {
  name?: string | null;
  value?: string | null;
}

export interface EchoItem {
  name?: string | null;
  slot?: string | null;
  set_name?: string | null;
  cost?: number | null;
  level?: number | null;
  main_stat?: string | null;
  sub_stats: SubStat[];
}

export interface WeaponState {
  name?: string | null;
  level?: number | null;
  rank?: number | null;
  main_stat?: string | null;
}

export interface CharacterSnapshot {
  character_name?: string | null;
  character_level?: number | null;
  role?: Role | null;
  weapon?: WeaponState | null;
  stats: StatBlock;
  echoes: EchoItem[];
  raw_text: string;
}

export interface VisionExtractionResult {
  screen_type: ScreenType;
  snapshot: CharacterSnapshot;
  uncertain_fields: string[];
  warnings: string[];
  confidence?: number | null;
  raw_model_output?: string | null;
}

export interface BuildRule {
  character_name: string;
  role: Role;
  recommended_sets: string[];
  priority_stats: string[];
  useful_sub_stats: string[];
  bad_sub_stats: string[];
  recommended_weapons: string[];
  notes?: string | null;
  source_links: string[];
  game_version?: string | null;
}

export interface CharacterCatalogItem {
  id: number;
  name: string;
  element?: string | null;
  weapon_type?: string | null;
  rarity?: number | null;
  image?: string | null;
  splash_image?: string | null;
  default_sonata?: string | null;
  sonata_fallbacks: string[];
  default_weapon?: string | null;
  bonus_stats: string[];
  role: Role;
  source?: string | null;
}

export interface PickupScheduleItem {
  id: string;
  year: number;
  month: number;
  day?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  version?: string | null;
  phase?: string | null;
  category: "first_pickup" | "rerun_1" | "rerun_2" | "rerun_3";
  label_ko: string;
  characters: string[];
  appearance_no?: number | null;
  status?: string | null;
  notes_ko?: string | null;
  source_links: string[];
}

export interface GameUpdateSummary {
  id: string;
  version: string;
  title_ko: string;
  release_date_kst?: string | null;
  summary_ko: string;
  highlights_ko: string[];
  source_links: string[];
}

export interface Diagnosis {
  target_type: "echo" | "character" | "account" | "team";
  target_name?: string | null;
  grade: Grade;
  score: number;
  reasons: string[];
  recommended_actions: string[];
}

export interface AnalysisSession {
  id: string;
  created_at: string;
  image_filename?: string | null;
  extraction: VisionExtractionResult;
  diagnoses: Diagnosis[];
  report: string;
  metadata: Record<string, unknown>;
}

export interface AnalyzeResponse {
  snapshot: CharacterSnapshot;
  diagnoses: Diagnosis[];
  report: string;
}
