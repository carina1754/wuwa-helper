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

// --- Echo main-stat options + max (level-25, 5★) values, by cost ------------
// value = the level-25 maximum; lower levels scale linearly (WuWa echo curve is
// ~linear from a small base to the L25 max).
type MainOpt = { key: StatKey; max: number };
export const ECHO_MAIN: Record<number, MainOpt[]> = {
  1: [
    { key: "hp", max: 2280 }, { key: "atkPct", max: 18.0 },
    { key: "hpPct", max: 22.8 }, { key: "defPct", max: 18.0 },
  ],
  3: [
    { key: "atkPct", max: 30.0 }, { key: "hpPct", max: 30.0 }, { key: "defPct", max: 38.0 },
    { key: "energyRegen", max: 32.0 },
    { key: "glacioDmg", max: 30.0 }, { key: "fusionDmg", max: 30.0 }, { key: "electroDmg", max: 30.0 },
    { key: "aeroDmg", max: 30.0 }, { key: "spectroDmg", max: 30.0 }, { key: "havocDmg", max: 30.0 },
  ],
  4: [
    { key: "crit", max: 22.0 }, { key: "critDmg", max: 44.0 },
    { key: "atkPct", max: 33.0 }, { key: "hpPct", max: 33.0 }, { key: "defPct", max: 41.8 },
    { key: "atk", max: 150 }, { key: "healing", max: 26.4 },
  ],
};

// main stat value at a given echo level (0-25), linear from ~14% of max at L0.
export function echoMainValue(max: number, level: number): number {
  const t = Math.max(0, Math.min(25, level)) / 25;
  return max * (0.14 + 0.86 * t);
}

// --- Echo sub-stat pool + roll range (per single roll) ----------------------
export const ECHO_SUB: { key: StatKey; min: number; max: number }[] = [
  { key: "hp", min: 320, max: 580 },
  { key: "atk", min: 30, max: 70 },
  { key: "def", min: 30, max: 70 },
  { key: "hpPct", min: 6.4, max: 11.6 },
  { key: "atkPct", min: 6.4, max: 11.6 },
  { key: "defPct", min: 8.1, max: 14.7 },
  { key: "crit", min: 6.3, max: 10.5 },
  { key: "critDmg", min: 12.6, max: 21.0 },
  { key: "energyRegen", min: 5.6, max: 14.9 },
  { key: "skillDmg", min: 6.4, max: 12.4 },
  { key: "basicDmg", min: 6.4, max: 11.6 },
  { key: "heavyDmg", min: 6.4, max: 11.6 },
  { key: "liberationDmg", min: 6.4, max: 11.6 },
];
export const subMax = (key: StatKey) => ECHO_SUB.find((s) => s.key === key)?.max ?? 0;
// sub-stat slots by echo grade (rarity/star)
export const SUB_SLOTS: Record<number, number> = { 5: 5, 4: 4, 3: 3, 2: 2, 1: 1 };
export const ECHO_COST_BUDGET = 12;

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
    const opt = (ECHO_MAIN[e.cost] ?? []).find((o) => o.key === e.main);
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
export function defaultMain(cost: number): StatKey {
  const opts = ECHO_MAIN[cost] ?? ECHO_MAIN[1];
  return opts[0].key;
}

export function echoFromCodex(e: CodexEcho): EchoBuild {
  const cost = e.cost ?? 1;
  return { echoId: e.id, cost, grade: e.rarity >= 3 ? 5 : e.rarity + 2, level: 25, main: defaultMain(cost), subs: [] };
}
