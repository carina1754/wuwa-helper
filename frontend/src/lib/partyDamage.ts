// 파티 "상대 딜 지수" 계산. AI 추천은 캐릭/무기/에코 id만 주고 실제 서브스탯·
// 로테이션이 없으므로, 모든 캐릭터에 동일한 "표준 빌드 가정"(90레벨·추천무기 R1 L90·
// 이상적 에코/서브스탯 패키지)을 적용해 build.ts의 실제 데미지 공식을 돌린다.
// 절대 인게임 수치가 아니라 조합 간 비교용 상대 지수로만 의미가 있다.
import {
  computeStats,
  emptyBuild,
  type GameConfig,
  type ResonatorBuild,
  skillDamage,
  type StatKey,
  weaponBuffs,
} from "./build";
import type { CodexResonator, CodexWeapon, Recommendation } from "./types";

const ELEM_DMG_KEY: Record<string, StatKey> = {
  응결: "glacioDmg",
  용융: "fusionDmg",
  전도: "electroDmg",
  기류: "aeroDmg",
  회절: "spectroDmg",
  인멸: "havocDmg",
};

// 엔드게임 DPS 기준 대표 에코/서브스탯 묶음(크리율≈70/크리피해≈250, 공% + 속성피해).
// 전 캐릭터 공통 적용 → 캐릭터 차이는 기초공격력·무기·스킬 배율·속성에서만 나온다.
function stdEchoPackage(element: string | null | undefined): { key: StatKey; value: number }[] {
  const pkg: { key: StatKey; value: number }[] = [
    { key: "atkPct", value: 60 },
    { key: "atk", value: 150 },
    { key: "crit", value: 65 },
    { key: "critDmg", value: 100 },
  ];
  const ek = element ? ELEM_DMG_KEY[element] : undefined;
  if (ek) pkg.push({ key: ek, value: 60 });
  return pkg;
}

export interface PartyDamageRow {
  resonatorId: string;
  index: number; // 상대 지수(총합의 일부)
  share: number; // 0..1
}
export interface PartyDamage {
  total: number;
  rows: PartyDamageRow[];
}

/** 추천 팀의 상대 딜 지수. 데이터가 부족하면 null. */
export function computePartyDamage(
  rec: Recommendation,
  resoById: Map<number, CodexResonator>,
  weaponById: Map<string, CodexWeapon>,
  config: GameConfig | null,
): PartyDamage | null {
  if (!rec.team?.length) return null;

  const raw: { resonatorId: string; value: number }[] = [];
  for (const pick of rec.team) {
    const reso = resoById.get(Number(pick.resonator_id));
    if (!reso) {
      raw.push({ resonatorId: pick.resonator_id, value: 0 });
      continue;
    }
    const weapon = pick.weapon ? weaponById.get(pick.weapon.id) ?? null : null;
    const build: ResonatorBuild = { ...emptyBuild(), weaponId: weapon?.id ?? null, weaponLevel: 90, weaponRank: 1 };
    const wb = weapon ? weaponBuffs(weapon, build.weaponRank) : null;
    const extra = [...stdEchoPackage(reso.element), ...(wb?.always ?? [])];
    const stats = computeStats(reso, weapon, build, config, extra);
    const boost = wb?.boost ?? 0;

    // 대표 로테이션 대용: 데미지 배율이 있는 모든 스킬을 Lv.10 기준 1회씩 합산.
    let sum = 0;
    for (const s of reso.skills ?? []) {
      if (!s.damage?.length) continue;
      const mult = s.damage.reduce((a, d) => {
        const r = d.rates[Math.min(9, d.rates.length - 1)] ?? "0";
        return a + (parseFloat(r) || 0);
      }, 0);
      if (mult <= 0) continue;
      sum += skillDamage(stats, mult, reso.element, s.SkillType, { boost });
    }
    raw.push({ resonatorId: pick.resonator_id, value: sum });
  }

  const totalRaw = raw.reduce((a, r) => a + r.value, 0);
  if (totalRaw <= 0) return null;
  return {
    total: Math.round(totalRaw / 1000),
    rows: raw.map((r) => ({
      resonatorId: r.resonatorId,
      index: Math.round(r.value / 1000),
      share: r.value / totalRaw,
    })),
  };
}
