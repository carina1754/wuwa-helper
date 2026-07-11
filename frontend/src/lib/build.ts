// WuWa build math for the party builder: character (encore level curves) +
// weapon (encore curves) + 5 echoes (standard WuWa main/sub-stat tables).
// Echo main-stat / sub-stat values are game constants (not in encore), encoded
// here as the canonical WuWa main/sub-stat reference values.
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
  // skills[] 배열 인덱스 -> 스킬 레벨(1-10). 미지정 스킬은 서버에서 Lv.10로 계산.
  skillLevels?: Record<number, number>;
  // 공명 사슬(S0-S6). 보유 시퀀스 단계 수 — 서버가 S1..sequence 노드 효과를 딜에 반영.
  sequence?: number;
};

export function emptyBuild(): ResonatorBuild {
  return { level: 90, weaponId: null, weaponLevel: 90, weaponRank: 1, echoes: [null, null, null, null, null], skillLevels: {}, sequence: 0 };
}

const curveAt = (curve: { level: number; value: number }[] | undefined, level: number): number => {
  if (!curve?.length) return 0;
  return (curve.find((c) => c.level === level) ?? curve[curve.length - 1])?.value ?? 0;
};

// Final stats: WuWa formula — %-stats boost the (character + weapon) base; flats add on top.
// Parse a simple always-on set effect ("용융 피해가 10% 증가된다") into a stat delta.
const ELEM_DMG: Record<string, StatKey> = {
  응결: "glacioDmg", 용융: "fusionDmg", 전도: "electroDmg", 기류: "aeroDmg", 회절: "spectroDmg", 인멸: "havocDmg",
};
export function parseSetEffect(text: string | null | undefined): { key: StatKey; value: number } | null {
  if (!text) return null;
  const m = text.match(/([가-힣·\s]+?)(?:가|이)\s*([\d.]+)%\s*증가/);
  if (!m) return null;
  const value = parseFloat(m[2]);
  const name = m[1].trim();
  for (const [el, k] of Object.entries(ELEM_DMG)) if (name.includes(el)) return { key: k, value };
  if (name.includes("공명 스킬")) return { key: "skillDmg", value };
  if (name.includes("공명 해방")) return { key: "liberationDmg", value };
  if (name.includes("일반 공격")) return { key: "basicDmg", value };
  if (name.includes("강공격")) return { key: "heavyDmg", value };
  if (name.includes("공격력")) return { key: "atkPct", value };
  if (name.includes("방어력")) return { key: "defPct", value };
  if (name.includes("HP")) return { key: "hpPct", value };
  if (name.includes("크리티컬 피해")) return { key: "critDmg", value };
  if (name.includes("크리티컬")) return { key: "crit", value };
  if (name.includes("공명 효율")) return { key: "energyRegen", value };
  if (name.includes("치료")) return { key: "healing", value };
  return null;
}

export type SonataSet = { name_ko: string; two_piece?: string | null; five_piece?: string | null };
// The set with the most equipped echoes; its 2-set (and 5-set at 5) always-on effects apply.
export function activeSetBonuses(
  build: ResonatorBuild,
  echoSonata: (id: string) => string[],
  setByName: Map<string, SonataSet>,
): { name: string; count: number; bonuses: { key: StatKey; value: number }[] } | null {
  const counts = new Map<string, number>();
  for (const e of build.echoes) {
    if (!e) continue;
    for (const s of echoSonata(e.echoId)) counts.set(s, (counts.get(s) ?? 0) + 1);
  }
  let best: { name: string; count: number } | null = null;
  for (const [name, count] of counts) if (count >= 2 && (!best || count > best.count)) best = { name, count };
  if (!best) return null;
  const set = setByName.get(best.name);
  const bonuses: { key: StatKey; value: number }[] = [];
  const two = parseSetEffect(set?.two_piece);
  if (two) bonuses.push(two);
  if (best.count >= 5) {
    const five = parseSetEffect(set?.five_piece);
    if (five) bonuses.push(five);
  }
  return { name: best.name, count: best.count, bonuses };
}

export function computeStats(
  reso: CodexResonator,
  weapon: CodexWeapon | null,
  build: ResonatorBuild,
  config: GameConfig | null,
  extra: { key: StatKey; value: number }[] = [],
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
  for (const s of extra) addStat(s.key, s.value); // sonata sets + weapon passive buffs (from caller)

  // 포르테(스킬트리) 고정 스탯 보너스 — 인게임 패널에 항상 반영되는 값(예: +공격력%·+크리 피해·+속성 피해).
  if (reso.forte_bonus) {
    for (const [key, value] of Object.entries(reso.forte_bonus)) addStat(key as StatKey, value);
  }

  out.hp = (baseHp) * (1 + pct.hpPct / 100) + flat.hp;
  out.atk = (baseAtk + weaponAtk) * (1 + pct.atkPct / 100) + flat.atk;
  out.def = (baseDef) * (1 + pct.defPct / 100) + flat.def;
  return out;
}

export const buildCost = (build: ResonatorBuild) =>
  build.echoes.reduce((s, e) => s + (e?.cost ?? 0), 0);

// Weapon passives scale by refine rank as slash-lists ("4%/6.2%/8.4%/10.6%/12.8%").
// Substitute each list with the value for the given rank (1-5).
export function weaponDescAtRank(desc: string | null | undefined, rank: number): string {
  const text = (desc ?? "").replace(/<[^>]+>/g, "");
  return text.replace(/(\d+(?:\.\d+)?%?)(?:\s*\/\s*\d+(?:\.\d+)?%?)+/g, (m) => {
    const parts = m.split("/").map((p) => p.trim());
    return parts[Math.min(Math.max(rank - 1, 0), parts.length - 1)] ?? parts[parts.length - 1];
  });
}

// Parse weapon passive stat/boost buffs from the description, split into
// ALWAYS-on (unconditional leading clauses) vs CONDITIONAL (trigger-gated), each
// scaled by refine rank and multiplied by its max stack count. The party builder
// applies `always` unconditionally and `conditional`+`boost` only under the
// "full uptime" assumption. Free-text parse → conservative: only recognized stat
// phrases are captured; anything ambiguous is left out.
export type WeaponBuff = { key: StatKey; value: number };
const WEAPON_ELEM_DMG: [string, StatKey][] = [
  ["응결", "glacioDmg"], ["용융", "fusionDmg"], ["전도", "electroDmg"],
  ["기류", "aeroDmg"], ["회절", "spectroDmg"], ["인멸", "havocDmg"],
];
// A sentence is conditional if it names a trigger/gate rather than a flat buff.
const WEAPON_COND_RE = /시|경우|후|때|이상|이하|발동|추가|입힌|입힐|명중|처치|소모|획득|전환|스택|중첩|상태|동안/;
export function weaponBuffs(
  weapon: CodexWeapon | null,
  rank: number,
): { always: WeaponBuff[]; conditional: WeaponBuff[]; boost: number } {
  const always: Partial<Record<StatKey, number>> = {};
  const cond: Partial<Record<StatKey, number>> = {};
  let boost = 0;
  if (!weapon?.desc) return { always: [], conditional: [], boost: 0 };
  const text = weaponDescAtRank(weapon.desc, rank);
  // split on sentence boundaries, but NOT on the "." inside decimals (25.6%)
  for (const sentence of text.split(/[。\n]+|\.(?!\d)/)) {
    if (!sentence.trim()) continue;
    const conditional = WEAPON_COND_RE.test(sentence);
    const bucket = conditional ? cond : always;
    const stackM = sentence.match(/최대\s*(\d+)\s*스택/);
    const stacks = stackM ? Math.max(1, parseInt(stackM[1], 10)) : 1;
    const add = (key: StatKey, v: number) => { bucket[key] = (bucket[key] ?? 0) + v * stacks; };
    // "전체 속성 피해 보너스가 N% 증가" → all six element keys (char uses only its own)
    for (const m of sentence.matchAll(/전체\s*속성\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g))
      for (const [, key] of WEAPON_ELEM_DMG) add(key, parseFloat(m[1]));
    // "일반 공격, 강공격 피해 보너스가 N% 증가" → both; consume so singles don't double-count
    const rest = sentence.replace(
      /일반\s*공격,\s*강공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g,
      (_m, v: string) => { add("basicDmg", parseFloat(v)); add("heavyDmg", parseFloat(v)); return " "; },
    );
    const singles: [RegExp, StatKey][] = [
      [/일반\s*공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g, "basicDmg"],
      [/강공격\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g, "heavyDmg"],
      [/공명\s*스킬\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g, "skillDmg"],
      [/공명\s*해방\s*피해\s*보너스[가이을를]?\s*([\d.]+)\s*%\s*증가/g, "liberationDmg"],
      [/공격력[이가]\s*([\d.]+)\s*%\s*증가/g, "atkPct"],
      [/방어력[이가]\s*([\d.]+)\s*%\s*증가/g, "defPct"],
      [/(?:HP|생명력)[이가]\s*([\d.]+)\s*%\s*증가/g, "hpPct"],
      [/크리티컬\s*피해[를이가을]?\s*([\d.]+)\s*%\s*증가/g, "critDmg"],
      [/크리티컬[이가]\s*([\d.]+)\s*%\s*증가/g, "crit"],
      [/공명\s*효율[이가]?\s*([\d.]+)\s*%\s*증가/g, "energyRegen"],
    ];
    for (const [re, key] of singles) {
      for (const m of rest.matchAll(re)) add(key, parseFloat(m[1]));
    }
    for (const [name, key] of WEAPON_ELEM_DMG) {
      for (const m of rest.matchAll(new RegExp(`${name}\\s*(?:효과\\s*)?피해\\s*보너스[가이을를]?\\s*([\\d.]+)\\s*%\\s*증가`, "g"))) add(key, parseFloat(m[1]));
    }
    // boost clauses ("... N% 부스트") — treated as conditional (trigger-gated)
    for (const m of rest.matchAll(/([\d.]+)\s*%\s*부스트/g)) boost += parseFloat(m[1]) * stacks;
  }
  const toArr = (o: Partial<Record<StatKey, number>>): WeaponBuff[] =>
    (Object.entries(o) as [StatKey, number][])
      .filter(([, v]) => Number.isFinite(v) && v !== 0)
      .map(([key, value]) => ({ key, value }));
  return { always: toArr(always), conditional: toArr(cond), boost };
}

// pick the default main stat for an echo of a given cost
export function defaultMain(config: GameConfig, cost: number): StatKey {
  return echoMainOptions(config, cost)[0]?.key ?? "atkPct";
}

export function echoFromCodex(e: CodexEcho, config: GameConfig): EchoBuild {
  const cost = e.cost ?? 1;
  return { echoId: e.id, cost, grade: e.rarity >= 3 ? 5 : e.rarity + 2, level: 25, main: defaultMain(config, cost), subs: [] };
}

// --- Damage (normal skill) — phro.love formula --------------------------------
// Damage = Multiplier × FinalATK × Crit × DMGbonus × Boost × RES × DEF × Taken × Total
export const ELEMENT_DMG_KEY: Record<string, StatKey> = {
  응결: "glacioDmg", 용융: "fusionDmg", 전도: "electroDmg", 기류: "aeroDmg", 회절: "spectroDmg", 인멸: "havocDmg",
};
export function skillTypeDmgKey(type: string | null | undefined): StatKey | null {
  const t = type ?? "";
  if (t.includes("강공격")) return "heavyDmg";
  if (t.includes("일반") || t.includes("기본")) return "basicDmg";
  if (t.includes("공명 스킬") || t.includes("공명스킬")) return "skillDmg";
  if (t.includes("공명 해방") || t.includes("공명해방")) return "liberationDmg";
  return null; // 변주/반주/협동/에코 등은 표준 보너스 스탯이 없음
}

export const critMultiplier = (stats: Record<StatKey, number>) =>
  1 + (stats.crit / 100) * (stats.critDmg / 100 - 1);

// (800 + 8·myLv) / (800 + 8·myLv + (792 + 8·enemyLv)(1-ignore)(1-reduce))
export function defMultiplier(myLevel = 90, enemyLevel = 90, defIgnore = 0, defReduce = 0): number {
  return (800 + 8 * myLevel) / (800 + 8 * myLevel + (792 + 8 * enemyLevel) * (1 - defIgnore) * (1 - defReduce));
}

// All adjustable conditions from the phro.love formula.
export type DamageOpts = {
  myLevel?: number;
  enemyLevel?: number;
  enemyRes?: number; // 0.2 = 20%
  resShred?: number; // 저항 무시 (adds to 0.8 base)
  defIgnore?: number; // 방어 무시 (0..1)
  defReduce?: number; // 방어 감소 (0..1)
  boost?: number; // 부스트 % (independent)
  dmgTaken?: number; // 받는 피해 % (independent)
  totalDmg?: number; // 최종 피해 % (independent)
  bonusPct?: number; // extra 피해증가 % (buffs)
  fixedDmg?: number; // 고정 추가 피해 (added last)
};

function resMultiplier(enemyRes: number, resShred: number): number {
  // phro.love sim: 0.8 + 저항무시, overpen (negative net res) counts half.
  const net = enemyRes - resShred; // effective enemy resistance
  const raw = 1 - net; // = 0.8 at 20% with no shred
  return raw > 1 ? 1 + (raw - 1) * 0.5 : raw;
}

export function skillDamage(
  stats: Record<StatKey, number>,
  multiplierPct: number,
  element: string | null | undefined,
  skillType: string | null | undefined,
  opts: DamageOpts = {},
): number {
  const {
    myLevel = 90, enemyLevel = 90, enemyRes = 0.2, resShred = 0,
    defIgnore = 0, defReduce = 0, boost = 0, dmgTaken = 0, totalDmg = 0, bonusPct = 0, fixedDmg = 0,
  } = opts;
  const elemKey = element ? ELEMENT_DMG_KEY[element] : undefined;
  const typeKey = skillTypeDmgKey(skillType);
  const dmgBonus = 1 + ((elemKey ? stats[elemKey] : 0) + (typeKey ? stats[typeKey] : 0) + bonusPct) / 100;
  const res = resMultiplier(enemyRes, resShred);
  const def = defMultiplier(myLevel, enemyLevel, defIgnore, defReduce);
  const base =
    (multiplierPct / 100) * stats.atk * critMultiplier(stats) * dmgBonus *
    (1 + boost / 100) * res * def * (1 + dmgTaken / 100) * (1 + totalDmg / 100);
  return base + fixedDmg;
}

// --- Anomaly (이상) damage — phro.love ----------------------------------------
export type AnomalyType = { key: string; mode: string; coef?: number; maxStack?: number; overBonus?: number; stack1?: number; perStack?: number; stack1Mult?: number; base?: number; defPerStack?: number; maxDef?: number };
export type AnomalyConfig = { base: Record<string, number>; types: Record<string, AnomalyType> };
// 암흑(디버프형) 방어 감소 = 스택 × 2% (최대 6%). 직접 피해는 없음.
export function anomalyDefReduce(cfg: AnomalyConfig, type: string, stacks: number): number {
  const t = cfg.types[type];
  if (!t || t.mode !== "debuff") return 0;
  return Math.min(t.maxDef ?? 0.06, (t.defPerStack ?? 0.02) * Math.max(0, stacks));
}
