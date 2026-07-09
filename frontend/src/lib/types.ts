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
  image_url?: string | null;
}

export interface SiteUpdateEntry {
  id: string;
  date: string;
  version?: string | null;
  title_ko: string;
  description_ko: string;
}

export interface PickupBannerCharacter {
  name_ko: string;
  avatar?: string | null;
  catalog_id?: number | null;
}

export interface PickupBannerWeapon {
  name_ko: string;
  icon?: string | null;
  rarity?: number | null;
  weapon_type?: string | null;
}

export interface PickupBanner {
  id: string;
  version: string;
  phase?: number | null;
  banner_name?: string | null;
  is_rerun: boolean;
  is_collab: boolean;
  characters: PickupBannerCharacter[];
  weapons: PickupBannerWeapon[];
  start_date?: string | null;
  end_date?: string | null;
}

export interface CodexSkillDamage {
  type?: string | null;
  prop?: string | null;
  name?: string | null;
  rates: string[]; // multiplier per skill level (index 0 = Lv.1)
}
export interface CodexSkill {
  SkillName?: string | null;
  SkillDescribe?: string | null;
  SkillType?: string | null;
  Icon?: string | null;
  damage?: CodexSkillDamage[] | null;
}

export interface CodexResonanceNode {
  NodeName?: string | null;
  AttributesDescription?: string | null;
}

export interface CodexResonator {
  id: number;
  name: string;
  name_en?: string | null;
  rarity: number;
  element?: string | null;
  weapon_type?: string | null;
  weapon_type_ko?: string | null;
  role: Role;
  image?: string | null;
  skills: CodexSkill[];
  resonance_chain: CodexResonanceNode[];
  stats: Record<string, number>;
  stat_curves?: Record<string, { level: number; value: number }[]> | null;
  max_level?: number | null;
  introduction?: string | null;
}

export interface CodexWeaponResonance {
  Name?: string | null;
}

export interface CodexWeapon {
  id: string;
  name_ko: string;
  name_en?: string | null;
  weapon_type?: string | null;
  weapon_type_ko?: string | null;
  rarity: number;
  desc?: string | null;
  attributes_description?: string | null;
  resonance?: CodexWeaponResonance | CodexWeaponResonance[] | null;
  icon?: string | null;
  properties?: {
    name?: string | null;
    base?: number | null;
    curve?: { level: number; value: number }[] | null;
    max?: number | null;
  }[] | null;
}

export interface CodexEchoSkill {
  DescriptionEx?: string | null;
  SkillCD?: number | null;
}

export interface CodexEcho {
  id: string;
  name_ko: string;
  name_en?: string | null;
  cost: number;
  rarity: number;
  sonata: string[];
  skill?: CodexEchoSkill | null;
  icon?: string | null;
}

export interface SonataSet {
  id: string;
  name_ko: string;
  icon?: string | null;
  two_piece?: string | null;
  five_piece?: string | null;
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

// --- AI coach ---
export interface AiProfile {
  union_level?: number | null;
  owned_characters: string[];
  desired_characters: string[];
  play_style?: string | null;
  note?: string | null;
}

export interface AiMessage {
  role: "user" | "assistant";
  content: string;
}

export interface WeaponPick {
  id: string;
  alt_ids: string[];
  reason?: string | null;
}

export interface EchoPick {
  sonata_ids: string[];
  main_echo_id?: string | null;
  main_stats: Record<string, string>;
  sub_stats?: string[];
}

export interface TeamPick {
  resonator_id: string;
  role?: Role | null;
  reason?: string | null;
  weapon?: WeaponPick | null;
  echo?: EchoPick | null;
  priority?: number | null;
}

export interface Recommendation {
  summary: string;
  team: TeamPick[];
  upgrade_order: string[];
}

export interface AiChatResponse {
  reply: string;
  recommendation?: Recommendation | null;
  is_final: boolean;
}

export interface AiRecommendationRecord {
  id: string;
  user_id?: string | null;
  created_at: string;
  profile: AiProfile;
  conversation: AiMessage[];
  recommendation: Recommendation;
  title?: string | null;
}

export interface AiRecommendationCreate {
  user_id?: string | null;
  profile: AiProfile;
  conversation: AiMessage[];
  recommendation: Recommendation;
  title?: string | null;
}
