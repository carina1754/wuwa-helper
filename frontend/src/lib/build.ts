// WuWa build math for the party builder: character (encore level curves) +
// weapon (encore curves) + 5 echoes (standard WuWa main/sub-stat tables).
// Echo main-stat / sub-stat values are game constants (not in encore), encoded
// here to match what wuthering.gg's builder shows.
import type { CodexResonator, CodexWeapon, CodexEcho } from "./types";

export type StatKey =
  | "hp" | "atk" | "def"
  | "hpPct" | "atkPct" | "defPct"
  | "crit" | "critDmg" | "energyRegen"
  | "healing"
  | "basicDmg" | "heavyDmg" | "skillDmg" | "liberationDmg"
  | "glacioDmg" | "fusionDmg" | "electroDmg" | "aeroDmg" | "spectroDmg" | "havocDmg";

export const STAT_LABEL: Record<StatKey, string> = {
  hp: "HP", atk: "공격력", def: "방어력",
  hpPct: "HP%", atkPct: "공격력%", defPct: "방어력%",
  crit: "크리티컬", critDmg: "크리티컬 피해", energyRegen: "공명 효율", healing: "치료 효과 보너스",
  basicDmg: "일반 공격 피해", heavyDmg: "강공격 피해", skillDmg: "공명 스킬 피해", liberationDmg: "공명 해방 피해",
  glacioDmg: "응결 피해", fusionDmg: "용융 피해", electroDmg: "전도 피해",
  aeroDmg: "기류 피해", spectroDmg: "회절 피해", havocDmg: "인멸 피해",
};

const PCT_STATS = new Set<StatKey>([
  "hpPct", "atkPct", "defPct", "crit", "critDmg", "energyRegen", "healing",
  "basicDmg", "heavyDmg", "skillDmg", "liberationDmg",
  "glacioDmg", "fusionDmg", "electroDmg", "aeroDmg", "spectroDmg", "havocDmg",
]);
export const isPct = (k: StatKey) => PCT_STATS.has(k);
export const fmtStat = (k: StatKey, v: number) =>
  isPct(k) ? `${v.toFixed(1)}%` : Math.round(v).toLocaleString();

// --- Echo stat config: sourced from the DB (/game-config), NOT hardcoded -----
export type EchoMainOpt = { key: StatKey; max: number };
export type EchoSubDef = { key: StatKey; min: number; max: number };
export type GameConfig = {
  costBudget: number;
  main: Record<string, EchoMainOpt[]>; // cost -> main-stat options (max at L25)
  sub: EchoSubDef[]; // sub-stat pool + per-roll range
  subSlots: Record<string, number>; // grade -> sub-stat slots
};

export const echoMainOptions = (cfg: GameConfig, cost: number): EchoMainOpt[] => cfg.main[String(cost)] ?? [];
export const subMax = (cfg: GameConfig, key: StatKey): number => cfg.sub.find((s) => s.key === key)?.max ?? 0;
export const subSlots = (cfg: GameConfig, grade: number): number => cfg.subSlots[String(grade)] ?? 0;

// main stat value at a given echo level (0-25), linear from ~14% of max at L0.
export function echoMainValue(max: number, level: number): number {
  const t = Math.max(0, Math.min(25, level)) / 25;
  return max * (0.14 + 0.86 * t);
}

// --- Build model ------------------------------------------------------------
export type EchoBuild = {
  echoId: string;
  cost: number;
  grade: number; // 1-5 star
  level: number; // 0-25
  main: StatKey;
  subs: { key: StatKey; value: number }[];
};
export type ResonatorBuild = {
  level: number; // 1-90
  weaponId: string | null;
  weaponLevel: number; // 1-90
  weaponRank: number; // 1-5
  echoes: (EchoBuild | null)[]; // length 5
};

export function emptyBuild(): ResonatorBuild {
  return { level: 90, weaponId: null, weaponLevel: 90, weaponRank: 1, echoes: [null, null, null, null, null] };
}

const curveAt = (curve: { level: number; value: number }[] | undefined, level: number): number => {
  if (!curve?.length) return 0;
  return (curve.find((c) => c.level === level) ?? curve[curve.length - 1])?.value ?? 0;
};

// Final stats: WuWa formula — %-stats boost the (character + weapon) base; flats add on top.
export function computeStats(
  reso: CodexResonator,
  weapon: CodexWeapon | null,
  build: ResonatorBuild,
  config: GameConfig | null,
): Record<StatKey, number> {
  const out = Object.fromEntries(Object.keys(STAT_LABEL).map((k) => [k, 0])) as Record<StatKey, number>;
  const curves = reso.stat_curves ?? {};
  const baseHp = curveAt(curves.Life, build.level);
  const baseAtk = curveAt(curves.Atk, build.level);
  const baseDef = curveAt(curves.Def, build.level);
  out.crit = curveAt(curves.Crit, build.level) || 5;
  out.critDmg = curveAt(curves.CritDamage, build.level) || 150;
  out.energyRegen = 100;

  // weapon: property[0] is the main ATK, property[1] the sub-stat (a %)
  let weaponAtk = 0;
  const pct = { hpPct: 0, atkPct: 0, defPct: 0 };
  const flat = { hp: 0, atk: 0, def: 0 };
  if (weapon?.properties?.length) {
    weaponAtk = curveAt(weapon.properties[0]?.curve ?? undefined, build.weaponLevel);
    const sub = weapon.properties[1];
    if (sub) {
      const v = curveAt(sub.curve ?? undefined, build.weaponLevel);
      const name = sub.name ?? "";
      if (name.includes("공격력")) pct.atkPct += v;
      else if (name.includes("HP")) pct.hpPct += v;
      else if (name.includes("방어력")) pct.defPct += v;
      else if (name.includes("크리티컬 피해")) out.critDmg += v;
      else if (name.includes("크리티컬")) out.crit += v;
      else if (name.includes("효율")) out.energyRegen += v;
    }
  }

  const addStat = (key: StatKey, value: number) => {
    if (key === "hpPct") pct.hpPct += value;
    else if (key === "atkPct") pct.atkPct += value;
    else if (key === "defPct") pct.defPct += value;
    else if (key === "hp") flat.hp += value;
    else if (key === "atk") flat.atk += value;
    else if (key === "def") flat.def += value;
    else out[key] += value;
  };

  for (const e of build.echoes) {
    if (!e) continue;
    const opt = config ? echoMainOptions(config, e.cost).find((o) => o.key === e.main) : undefined;
    if (opt) addStat(e.main, echoMainValue(opt.max, e.level));
    for (const s of e.subs) addStat(s.key, s.value);
  }

  out.hp = (baseHp) * (1 + pct.hpPct / 100) + flat.hp;
  out.atk = (baseAtk + weaponAtk) * (1 + pct.atkPct / 100) + flat.atk;
  out.def = (baseDef) * (1 + pct.defPct / 100) + flat.def;
  return out;
}

export const buildCost = (build: ResonatorBuild) =>
  build.echoes.reduce((s, e) => s + (e?.cost ?? 0), 0);

// pick the default main stat for an echo of a given cost
export function defaultMain(config: GameConfig, cost: number): StatKey {
  return echoMainOptions(config, cost)[0]?.key ?? "atkPct";
}

export function echoFromCodex(e: CodexEcho, config: GameConfig): EchoBuild {
  const cost = e.cost ?? 1;
  return { echoId: e.id, cost, grade: e.rarity >= 3 ? 5 : e.rarity + 2, level: 25, main: defaultMain(config, cost), subs: [] };
}
