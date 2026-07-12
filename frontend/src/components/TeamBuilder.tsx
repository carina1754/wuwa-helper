"use client";

import { useEffect, useMemo, useState } from "react";
import { Portal } from "./Portal";
import { signIn, useSession } from "next-auth/react";
import { aiChat, getCodexEchoes, getCodexResonators, getCodexWeapons, getGameConfig, getSonataSets, saveRecommendation, teamCalculate } from "@/lib/api";
import { mediaUrl } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { AiMessage, AiProfile, CodexEcho, CodexResonator, CodexWeapon, SimMemberIn, SimOpts, SonataSet, TeamCalcRequestBody, TeamCalcResult } from "@/lib/types";
import {
  activeSetBonuses,
  type AnomalyConfig,
  anomalyDefReduce,
  buildCost,
  computeStats,
  echoFromCodex,
  echoMainOptions,
  emptyBuild,
  fmtStat,
  type GameConfig,
  type ResonatorBuild,
  type StatKey,
  STAT_LABEL,
  subMax,
  subSlots,
  type WeaponBuff,
  weaponBuffs,
  weaponDescAtRank,
} from "@/lib/build";

export const PARTY_SIZE = 3;
export const STORAGE_KEY = "mj:party:v2";
const PANEL_KEYS: StatKey[] = ["hp", "atk", "def", "crit", "critDmg", "energyRegen"];
// 결과 카드에 항상 표시하는 핵심 스탯(그 외 0이 아닌 피해 보너스는 동적으로 추가)
const STAT_ROWS: StatKey[] = ["hp", "atk", "def", "crit", "critDmg", "energyRegen"];
// 팀 공유 버프로 자주 쓰는 스탯을 앞에 노출
const BUFF_KEYS: StatKey[] = ["atkPct", "atk", "critDmg", "crit", "skillDmg", "basicDmg", "heavyDmg", "liberationDmg", "fusionDmg", "glacioDmg", "electroDmg", "aeroDmg", "spectroDmg", "havocDmg"];

type UiOpts = { enemyLevel: number; enemyRes: number; resShred: number; defIgnore: number; defReduce: number; boost: number; bonusPct: number; fullUptime: boolean };
type NumericOptKey = Exclude<keyof UiOpts, "fullUptime">;
const DEFAULT_OPTS: UiOpts = { enemyLevel: 90, enemyRes: 20, resShred: 0, defIgnore: 0, defReduce: 0, boost: 0, bonusPct: 0, fullUptime: true };

const img = mediaUrl;
export function ring(r: number): string {
  return r >= 5 ? "ring-[var(--gold)]" : "ring-[color-mix(in_srgb,var(--accent)_60%,transparent)]";
}

export type Slot = { resonatorId: number | null; build: ResonatorBuild };
export const newParty = (): Slot[] => Array.from({ length: PARTY_SIZE }, () => ({ resonatorId: null, build: emptyBuild() }));

// 코덱스에 스킬 배율 데이터가 없는 공명자(예: 방랑자/로버 — 소스가 주인공 스킬을 제공하지 않음)는
// 엔진이 개인 피해를 0으로 반환한다. 오해를 부르는 "0" 대신 명확한 안내를 띄우려고 미리 감지한다.
function noSkillData(reso: CodexResonator | null | undefined): boolean {
  return !!reso && !(reso.skills ?? []).some((s) => (s.damage?.length ?? 0) > 0);
}

export function TeamBuilder() {
  const { t } = useLanguage();
  const [resos, setResos] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [echoes, setEchoes] = useState<CodexEcho[]>([]);
  const [config, setConfig] = useState<GameConfig | null>(null);
  const [anomaly, setAnomaly] = useState<AnomalyConfig | null>(null);
  const [sonata, setSonata] = useState<SonataSet[]>([]);
  const [party, setParty] = useState<Slot[]>(newParty);
  const [editing, setEditing] = useState<number | null>(null);
  const [picker, setPicker] = useState<null | { kind: "resonator" | "weapon" | "echo"; slot: number; echoIdx?: number }>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiStatus, setAiStatus] = useState("");
  const [mainDpsId, setMainDpsId] = useState<number | null>(null); // 사용자가 지정한 메인 딜러(역할 태그 우선)
  const { data: session } = useSession();
  const userId = session?.user?.email ?? null;

  // 시뮬 조건(파티 전체 공유 — 적 조건·팀 버프)
  const [opts, setOpts] = useState<UiOpts>(DEFAULT_OPTS);
  const [defShredPct, setDefShredPct] = useState<number | null>(null); // null = 자동(암흑 감지)
  const [teamBuffs, setTeamBuffs] = useState<{ key: StatKey; value: number }[]>([]);
  const [result, setResult] = useState<TeamCalcResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getCodexResonators().then(setResos).catch(() => {});
    getCodexWeapons().then(setWeapons).catch(() => {});
    getCodexEchoes().then(setEchoes).catch(() => {});
    getGameConfig()
      .then((c) => {
        setConfig((c?.echo_stats as GameConfig) ?? null);
        setAnomaly((c?.anomaly as AnomalyConfig) ?? null);
      })
      .catch(() => {});
    getSonataSets().then(setSonata).catch(() => {});
  }, []);
  useEffect(() => {
    try {
      const s = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
      if (Array.isArray(s) && s.length === PARTY_SIZE) setParty(s);
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(party));
    } catch {
      /* ignore */
    }
  }, [party]);

  const resoById = useMemo(() => new Map(resos.map((r) => [r.id, r])), [resos]);
  const weaponById = useMemo(() => new Map(weapons.map((w) => [w.id, w])), [weapons]);
  const echoById = useMemo(() => new Map(echoes.map((e) => [e.id, e])), [echoes]);
  // one representative echo per name (source lists id/rarity variants)
  const echoList = useMemo(() => {
    const m = new Map<string, CodexEcho>();
    for (const e of echoes) {
      const cur = m.get(e.name_ko);
      if (!cur || (e.rarity ?? 0) > (cur.rarity ?? 0)) m.set(e.name_ko, e);
    }
    return [...m.values()];
  }, [echoes]);

  const setByName = useMemo(() => new Map(sonata.map((s) => [s.name_ko, s])), [sonata]);
  const echoSonata = (id: string) => echoById.get(id)?.sonata ?? [];
  const bonusesFor = (b: ResonatorBuild) => activeSetBonuses(b, echoSonata, setByName)?.bonuses ?? [];
  // 파티에 인멸(암흑) 공명자가 있으면 적에게 암흑 디버프(방어 −6%) → 파티 전원 피해에 적용
  const autoDefShred = useMemo(() => {
    if (!anomaly) return 0;
    const hasHavoc = party.some((s) => (s.resonatorId != null ? resoById.get(s.resonatorId)?.element : null) === "인멸");
    return hasHavoc ? anomalyDefReduce(anomaly, "암흑", 100) : 0;
  }, [party, resoById, anomaly]);
  const shredPct = defShredPct ?? Math.round(autoDefShred * 100);

  const setSlot = (i: number, fn: (s: Slot) => Slot) => setParty((p) => p.map((s, j) => (j === i ? fn(s) : s)));
  const setBuild = (i: number, fn: (b: ResonatorBuild) => ResonatorBuild) => setSlot(i, (s) => ({ ...s, build: fn(s.build) }));

  const choose = (r: CodexResonator | CodexWeapon | CodexEcho) => {
    if (!picker) return;
    const { kind, slot, echoIdx } = picker;
    if (kind === "resonator") setSlot(slot, (s) => ({ ...s, resonatorId: (r as CodexResonator).id, build: { ...s.build, skillLevels: {} } }));
    else if (kind === "weapon") setBuild(slot, (b) => ({ ...b, weaponId: (r as CodexWeapon).id }));
    else if (kind === "echo" && echoIdx != null && config)
      setBuild(slot, (b) => ({ ...b, echoes: b.echoes.map((e, j) => (j === echoIdx ? echoFromCodex(r as CodexEcho, config) : e)) }));
    setPicker(null);
  };

  const partyFilled = party.every((s) => s.resonatorId != null);
  const filled = party.filter((s) => s.resonatorId != null).length;

  // 슬롯 → 서버 엔진 입력. 스킬 레벨은 빌드에서 개별 설정(미설정 스킬은 서버 기본 Lv.10). 풀 업타임 ON이면 조건부 공명 사슬/무기/킷 버프까지 이상적 로테이션 기준으로 반영.
  const slotToMember = (s: Slot): SimMemberIn | null => {
    if (s.resonatorId == null) return null;
    const b = s.build;
    const skillLevels = b.skillLevels && Object.keys(b.skillLevels).length ? b.skillLevels : undefined;
    return {
      reso_id: String(s.resonatorId),
      level: b.level,
      weapon_id: b.weaponId == null ? null : String(b.weaponId),
      weapon_level: b.weaponLevel,
      weapon_rank: b.weaponRank,
      echoes: b.echoes
        .filter((e): e is NonNullable<typeof e> => !!e)
        .map((e) => ({ echo_id: String(e.echoId), cost: e.cost, grade: e.grade, level: e.level, main: e.main, subs: e.subs.map((x) => ({ key: x.key, value: x.value })) })),
      skill_levels: skillLevels,
      sequence: b.sequence && b.sequence > 0 ? b.sequence : undefined,
      full_uptime: opts.fullUptime,
    };
  };

  const calculate = async () => {
    const members = party.map(slotToMember).filter((m): m is SimMemberIn => m !== null);
    if (!members.length) return;
    setBusy(true);
    setError("");
    const simOpts: SimOpts = {
      enemy_level: opts.enemyLevel,
      enemy_res: opts.enemyRes / 100,
      res_shred: opts.resShred / 100,
      def_ignore: opts.defIgnore / 100,
      def_reduce: opts.defReduce / 100,
      boost: opts.boost,
      bonus_pct: opts.bonusPct,
    };
    const body: TeamCalcRequestBody = {
      members,
      opts: simOpts,
      party_def_shred: shredPct / 100,
      team_buffs: teamBuffs.filter((b) => b.value !== 0),
    };
    try {
      setResult(await teamCalculate(body));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "계산에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const setOpt = (k: NumericOptKey, v: number) => setOpts((o) => ({ ...o, [k]: v }));
  const OPT_FIELDS: { key: NumericOptKey; label: string }[] = [
    { key: "enemyLevel", label: "적 레벨" },
    { key: "enemyRes", label: "적 저항%" },
    { key: "resShred", label: "저항 무시%" },
    { key: "defIgnore", label: "방어 무시%" },
    { key: "defReduce", label: "방어 감소%" },
    { key: "boost", label: "부스트%" },
    { key: "bonusPct", label: "피해증가%" },
  ];

  const ranked = result ? [...result.members].sort((a, b) => b.total - a.total) : [];

  /** 선택한 파티 구성을 한국어로 직렬화(기록에 남길 옵션 원문). */
  const describeParty = (): { names: string[]; text: string } => {
    const names: string[] = [];
    const lines: string[] = [];
    party.forEach((slot, i) => {
      const reso = slot.resonatorId != null ? resoById.get(slot.resonatorId) : null;
      if (!reso) return;
      names.push(reso.name);
      const b = slot.build;
      const weapon = b.weaponId ? weaponById.get(b.weaponId) : null;
      const wpart = weapon ? `무기 ${weapon.name_ko} R${b.weaponRank} Lv.${b.weaponLevel}` : "무기 미선택";
      const echoParts = b.echoes
        .filter((e): e is NonNullable<typeof e> => !!e)
        .map((e) => {
          const en = echoById.get(e.echoId)?.name_ko ?? "에코";
          const subs = e.subs.map((s) => STAT_LABEL[s.key]).join("·");
          return `${en}(메인 ${STAT_LABEL[e.main]}${subs ? `, 추옵 ${subs}` : ""})`;
        });
      const epart = echoParts.length ? `에코 ${echoParts.join(", ")}` : "에코 미선택";
      lines.push(`${i + 1}. ${reso.name} (Lv.${b.level}, ${reso.element}, ${t.roles[reso.role]}) — ${wpart}; ${epart}`);
    });
    return { names, text: lines.join("\n") };
  };

  /** 3명 완성된 파티를 LLM에 태워 AI 빌더와 동일 포맷으로 기록에 저장. */
  const analyzeAndSave = async () => {
    if (aiBusy || !partyFilled) return;
    if (!userId) {
      setAiStatus("기록을 저장하려면 구글 로그인이 필요해요.");
      return;
    }
    setAiBusy(true);
    setAiStatus("AI가 파티를 분석하는 중… (최대 30초)");
    const { names, text } = describeParty();
    const mainName = mainDpsId != null ? resos.find((r) => r.id === mainDpsId)?.name ?? null : null;
    const pinLine = mainName
      ? `\n\n메인딜 지정: ${mainName} (기본 역할 태그와 무관하게 이 공명자를 main_dps로 평가·빌드해줘)`
      : "";
    const firstMessage =
      "파티 빌딩에서 직접 구성한 파티입니다. 아래 구성을 평가하고, 각 캐릭터의 역할·무기·에코(소나타)·추천 추옵(최대 5개)과 파티 업그레이드 순서를 추천해줘. 정보가 충분하니 최종 추천으로 확정(is_final)해줘.\n\n[선택한 구성]\n" +
      text +
      pinLine;
    const profile: AiProfile = {
      owned_characters: names,
      desired_characters: names,
      play_style: null,
      note: "파티 빌딩 선택 구성:\n" + text,
    };
    const messages: AiMessage[] = [{ role: "user", content: firstMessage }];
    try {
      const res = await aiChat(messages, profile);
      if (!res.recommendation) {
        setAiStatus("추천을 생성하지 못했어요. 잠시 후 다시 시도해 주세요.");
        return;
      }
      const convo: AiMessage[] = [...messages, { role: "assistant", content: res.reply }];
      const saved = await saveRecommendation({
        user_id: userId,
        profile,
        conversation: convo,
        recommendation: res.recommendation,
        title: res.recommendation.summary || `${names.join(", ")} 파티`,
      });
      setAiStatus(`기록 탭에 저장했어요: ${saved.title ?? saved.recommendation.summary ?? "저장됨"}`);
    } catch {
      setAiStatus("분석에 실패했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-xl font-semibold text-[var(--fg)]">{t.teams.title}</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">공명자 3명의 캐릭터·무기·에코를 설정하면 서버 엔진이 파티 전체 피해와 기여도를 계산합니다.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {party.map((slot, i) => {
          const reso = slot.resonatorId != null ? resoById.get(slot.resonatorId) : null;
          const slotWeapon = slot.build.weaponId ? weaponById.get(slot.build.weaponId) ?? null : null;
          const stats = reso ? computeStats(reso, slotWeapon, slot.build, config, [...bonusesFor(slot.build), ...weaponBuffs(slotWeapon, slot.build.weaponRank).always]) : null;
          return (
            <div key={i} className="flex flex-col rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4" style={{ minHeight: 176 }}>
              {reso ? (
                <>
                  <div className="flex items-center gap-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={img(reso.image)} alt="" className={`h-11 w-11 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${ring(reso.rarity)}`} />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-[var(--fg)]">{reso.name}</div>
                      <div className="text-xs text-[var(--muted)]">Lv.{slot.build.level} · {reso.element} · {t.roles[reso.role]}</div>
                    </div>
                    <button type="button" onClick={() => setSlot(i, () => ({ resonatorId: null, build: emptyBuild() }))} className="ml-auto grid h-6 w-6 place-items-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]" aria-label="제거">✕</button>
                  </div>
                  {stats ? (
                    <dl className="mt-3 grid grid-cols-2 gap-1 text-xs">
                      {(["atk", "hp", "crit", "critDmg"] as StatKey[]).map((k) => (
                        <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2 py-1">
                          <dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt>
                          <dd className="font-medium text-[var(--fg)]">{fmtStat(k, stats[k])}</dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                  {noSkillData(reso) ? (
                    <div className="mt-2 rounded bg-[var(--surface-2)] px-2 py-1 text-[11px] leading-tight text-[#e0a04d]">⚠ 스킬 배율 데이터 없음 · 개인 피해 계산 불가</div>
                  ) : null}
                  <button type="button" onClick={() => setEditing(i)} className="mt-3 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] py-1.5 text-xs font-medium text-[var(--accent)] hover:border-[var(--accent)]">빌드 편집</button>
                </>
              ) : (
                <button type="button" onClick={() => setPicker({ kind: "resonator", slot: i })} className="flex h-full w-full flex-col items-center justify-center gap-2 text-[var(--muted)] hover:text-[var(--fg)]">
                  <span className="grid h-12 w-12 place-items-center rounded-full border border-dashed border-[var(--line-2)] text-xl">+</span>
                  <span className="text-xs">공명자 추가</span>
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* 시뮬 조건 — 파티 전체 공유(적 조건 + 팀 버프) */}
      <div className="grid gap-4 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 md:grid-cols-2">
        <div>
          <div className="mb-2 text-sm font-semibold text-[var(--fg)]">적 조건</div>
          <div className="grid grid-cols-2 gap-1.5 text-xs sm:grid-cols-3">
            {OPT_FIELDS.map((f) => (
              <label key={f.key} className="flex items-center justify-between gap-1 rounded bg-[var(--surface-2)] px-2 py-1">
                <span className="text-[var(--muted)]">{f.label}</span>
                <input type="number" value={opts[f.key]} onChange={(e) => setOpt(f.key, Number(e.target.value))} className="w-14 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 text-right text-[var(--fg)]" />
              </label>
            ))}
            <label className="flex items-center justify-between gap-1 rounded bg-[var(--surface-2)] px-2 py-1">
              <span className="text-[var(--muted)]">방어감소%{defShredPct == null ? "·자동" : ""}</span>
              <input type="number" value={shredPct} onChange={(e) => setDefShredPct(Number(e.target.value))} className="w-14 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 text-right text-[var(--fg)]" />
            </label>
          </div>
          <label className="mt-2 flex items-center gap-2 rounded bg-[var(--surface-2)] px-2 py-1.5 text-xs">
            <input type="checkbox" checked={opts.fullUptime} onChange={(e) => setOpts((o) => ({ ...o, fullUptime: e.target.checked }))} className="accent-[var(--accent)]" />
            <span className="text-[var(--fg)]">풀 업타임</span>
            <span className="text-[10px] text-[var(--muted)]">이상적 로테이션 기준 조건부 공명 사슬·무기·킷 버프 반영(끄면 상시 발동만)</span>
          </label>
          {autoDefShred > 0 && defShredPct == null ? (
            <p className="mt-1.5 text-[10px] text-[var(--accent)]">암흑(인멸) 자동 적용 · 적 방어 −{Math.round(autoDefShred * 100)}%</p>
          ) : null}
        </div>

        {/* 팀 공유 버프 */}
        <div>
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-semibold text-[var(--fg)]">팀 공유 버프</span>
            <button type="button" onClick={() => setTeamBuffs((b) => [...b, { key: "atkPct", value: 0 }])} className="text-xs text-[var(--accent)] hover:underline">+ 버프 추가</button>
          </div>
          <p className="mb-2 text-[11px] text-[var(--muted)]">서포터가 파티 전원에게 주는 버프(예: 공격력% +20). 모든 공명자 스탯에 더해집니다.</p>
          <div className="grid gap-1.5">
            {teamBuffs.length === 0 ? <div className="rounded bg-[var(--surface-2)] px-2 py-2 text-center text-xs text-[var(--muted)]">추가된 버프가 없습니다.</div> : null}
            {teamBuffs.map((b, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs">
                <select value={b.key} onChange={(e) => setTeamBuffs((arr) => arr.map((x, j) => (j === i ? { ...x, key: e.target.value as StatKey } : x)))} className="flex-1 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-[var(--fg)]">
                  {BUFF_KEYS.map((k) => <option key={k} value={k}>{STAT_LABEL[k]}</option>)}
                  {(Object.keys(STAT_LABEL) as StatKey[]).filter((k) => !BUFF_KEYS.includes(k)).map((k) => <option key={k} value={k}>{STAT_LABEL[k]}</option>)}
                </select>
                <input type="number" step="0.1" value={b.value} onChange={(e) => setTeamBuffs((arr) => arr.map((x, j) => (j === i ? { ...x, value: Number(e.target.value) } : x)))} className="w-16 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-right text-[var(--fg)]" />
                <button type="button" onClick={() => setTeamBuffs((arr) => arr.filter((_, j) => j !== i))} className="text-[var(--muted)] hover:text-[var(--fg)]" aria-label="삭제">✕</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 계산 */}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={calculate} disabled={!filled || busy} className="rounded-md bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-[var(--accent-ink)] hover:opacity-90 disabled:opacity-50">
          {busy ? "계산 중…" : "서버 엔진으로 계산"}
        </button>
        <span className="text-xs text-[var(--muted)]">공명자 {filled}명 · 스킬 레벨 개별 설정(기본 Lv.10)</span>
        {error ? <span className="text-xs text-[var(--danger,#e5484d)]">{error}</span> : null}
      </div>

      {/* 결과 */}
      {result ? (
        <div className="grid gap-3">
          <div className="flex items-baseline justify-between rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-3">
            <span className="text-sm font-semibold text-[var(--fg)]">팀 총 피해 (1사이클)</span>
            <span className="text-2xl font-bold tabular-nums text-[var(--accent)]">{Math.round(result.team_total).toLocaleString()}</span>
          </div>
          {ranked.map((m, rank) => {
            const reso = resoById.get(Number(m.reso_id));
            const share = result.team_total > 0 ? (m.total / result.team_total) * 100 : 0;
            const extras = (Object.keys(STAT_LABEL) as StatKey[]).filter((k) => !STAT_ROWS.includes(k) && Math.abs(m.stats[k] ?? 0) > 0.05);
            return (
              <div key={m.reso_id + rank} className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
                <div className="flex items-center gap-2">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[var(--surface-2)] text-xs font-bold text-[var(--fg-soft)]">{rank + 1}</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img(reso?.image)} alt="" className={`h-10 w-10 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${reso ? ring(reso.rarity) : ""}`} />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-[var(--fg)]">{m.name ?? reso?.name ?? m.reso_id}</div>
                    <div className="text-xs text-[var(--muted)]">{m.element ?? reso?.element} · 코스트 {m.cost}</div>
                  </div>
                  <div className="ml-auto text-right">
                    <div className="font-bold tabular-nums text-[var(--fg)]">{Math.round(m.total).toLocaleString()}</div>
                    <div className="text-xs text-[var(--muted)]">{share.toFixed(1)}%</div>
                  </div>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-2)]">
                  <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${share}%` }} />
                </div>

                <dl className="mt-3 grid grid-cols-2 gap-1.5 text-xs sm:grid-cols-3">
                  {STAT_ROWS.map((k) => (
                    <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2 py-1"><dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt><dd className="font-medium tabular-nums text-[var(--fg)]">{fmtStat(k, m.stats[k] ?? 0)}</dd></div>
                  ))}
                  {extras.map((k) => (
                    <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2 py-1"><dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt><dd className="font-medium tabular-nums text-[var(--accent)]">{fmtStat(k, m.stats[k] ?? 0)}</dd></div>
                  ))}
                </dl>

                {m.skills.length ? (
                  <dl className="mt-2 grid gap-1 text-sm">
                    {m.skills.map((s, j) => (
                      <div key={j} className="flex items-center justify-between gap-2 rounded bg-[var(--surface-2)] px-2.5 py-1.5">
                        <dt className="min-w-0 truncate text-[var(--muted)]">{s.name}{s.type ? ` · ${s.type}` : ""} <span className="text-[11px]">Lv.{s.level}</span></dt>
                        <dd className="shrink-0 font-medium tabular-nums text-[var(--fg)]">{Math.round(s.dmg).toLocaleString()}</dd>
                      </div>
                    ))}
                  </dl>
                ) : noSkillData(reso) ? (
                  <div className="mt-2 rounded bg-[var(--surface-2)] px-2.5 py-1.5 text-xs leading-relaxed text-[#e0a04d]">⚠ 스킬 배율 데이터가 없어 개인 피해를 계산할 수 없습니다. 방랑자(로버)는 버프·힐 서포터로 활용하세요.</div>
                ) : null}

                {(m.applied_team_buffs?.length ?? 0) > 0 ? (
                  <div className="mt-2 border-t border-dashed border-[var(--line)] pt-2">
                    <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">자동 적용 팀 버프</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {m.applied_team_buffs!.map((b, j) => (
                        <span key={j} className="rounded bg-[var(--surface-2)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--accent)]">{b}</span>
                      ))}
                    </div>
                  </div>
                ) : null}

                {(m.team_notes?.length ?? 0) > 0 ? (
                  <ul className="mt-2 grid gap-0.5 text-[11px] leading-relaxed text-[var(--muted)]">
                    {m.team_notes!.map((t, j) => (
                      <li key={j}>· {t}</li>
                    ))}
                  </ul>
                ) : null}

                {((m.anomaly_dmg ?? 0) > 0 || (m.anomaly_def_down ?? 0) > 0 || (m.tune_break_dmg ?? 0) > 0) ? (
                  <dl className="mt-2 grid gap-1 border-t border-dashed border-[var(--line)] pt-2 text-xs">
                    <div className="text-[10px] uppercase tracking-wide text-[var(--muted)]">상황부 · 딜 총합 미포함</div>
                    {m.anomaly_type && (m.anomaly_dmg ?? 0) > 0 ? (
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-[var(--muted)]">이상 피해 · {m.anomaly_type}</dt>
                        <dd className="shrink-0 tabular-nums text-[var(--fg-soft)]">{Math.round(m.anomaly_dmg!).toLocaleString()}</dd>
                      </div>
                    ) : null}
                    {(m.anomaly_def_down ?? 0) > 0 ? (
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-[var(--muted)]">이상 방깎 · {m.anomaly_type ?? "암흑"}</dt>
                        <dd className="shrink-0 tabular-nums text-[var(--fg-soft)]">-{((m.anomaly_def_down ?? 0) * 100).toFixed(0)}%</dd>
                      </div>
                    ) : null}
                    {(m.tune_break_dmg ?? 0) > 0 ? (
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-[var(--muted)]">조화도 파괴</dt>
                        <dd className="shrink-0 tabular-nums text-[var(--fg-soft)]">{Math.round(m.tune_break_dmg!).toLocaleString()}</dd>
                      </div>
                    ) : null}
                  </dl>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {/* AI 파티 분석 → 기록 저장 */}
      <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-[var(--fg)]">AI 파티 분석</div>
            <p className="mt-0.5 text-xs text-[var(--muted)]">
              공명자 3명을 모두 선택하면 구성을 AI가 평가해 추천 형식으로 기록에 저장합니다.
              {userId ? null : " 기록 저장은 구글 로그인이 필요해요."}
            </p>
          </div>
          {userId ? (
            <button
              type="button"
              onClick={analyzeAndSave}
              disabled={!partyFilled || aiBusy}
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[var(--accent-ink)] hover:opacity-90 disabled:opacity-50"
            >
              {aiBusy ? "분석 중…" : "AI로 분석·기록"}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void signIn("google", { callbackUrl: "/" })}
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[var(--accent-ink)] hover:opacity-90"
            >
              구글 로그인하고 기록
            </button>
          )}
        </div>
        {partyFilled ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-[var(--muted)]">메인 딜러 지정</span>
            <select
              value={mainDpsId ?? ""}
              onChange={(e) => setMainDpsId(e.target.value ? Number(e.target.value) : null)}
              className="rounded-md border border-[var(--line)] bg-[var(--surface-2)] px-2 py-1 text-[var(--fg)]"
            >
              <option value="">자동 (역할 태그 기준)</option>
              {party.map((s) =>
                s.resonatorId != null ? (
                  <option key={s.resonatorId} value={s.resonatorId}>
                    {resoById.get(s.resonatorId)?.name ?? s.resonatorId}
                  </option>
                ) : null,
              )}
            </select>
            <span className="text-[var(--faint)]">지정하면 역할 태그와 무관하게 그 캐릭터를 메인딜로 평가해요</span>
          </div>
        ) : null}
        {aiStatus ? <p className="mt-2 text-xs text-[var(--fg-soft)]">{aiStatus}</p> : null}
      </div>

      {/* build editor */}
      {editing != null && resoById.get(party[editing].resonatorId ?? -1) ? (
        <Portal>
          <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/60 p-4" role="dialog" aria-modal="true" onClick={() => setEditing(null)}>
            <div className="relative my-6 w-full max-w-lg rounded-lg border border-[var(--line)] bg-[var(--surface)] p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
              <BuildEditor
                reso={resoById.get(party[editing].resonatorId!)!}
                build={party[editing].build}
                weaponById={weaponById}
                echoById={echoById}
                setByName={setByName}
                config={config}
                slot={editing}
                t={t}
                onChange={(fn) => setBuild(editing, fn)}
                onPick={(p) => setPicker(p)}
                onClose={() => setEditing(null)}
              />
            </div>
          </div>
        </Portal>
      ) : null}

      {/* generic picker */}
      {picker ? (
        <PickerModal
          kind={picker.kind}
          resos={resos}
          weapons={picker.kind === "weapon" ? weapons.filter((w) => w.weapon_type_ko === resoById.get(party[picker.slot].resonatorId ?? -1)?.weapon_type_ko) : weapons}
          echoes={echoList}
          onChoose={choose}
          onClose={() => setPicker(null)}
          t={t}
        />
      ) : null}
    </section>
  );
}

// ---------------------------------------------------------------------------
const WEAPON_ELEM_KEYS: StatKey[] = ["glacioDmg", "fusionDmg", "electroDmg", "aeroDmg", "spectroDmg", "havocDmg"];
// compact label for weapon buffs; collapse the six element-dmg keys into "속성 피해"
function weaponBuffSummary(buffs: WeaponBuff[]): string {
  const elem = buffs.filter((b) => WEAPON_ELEM_KEYS.includes(b.key));
  const nonElem = buffs.filter((b) => !WEAPON_ELEM_KEYS.includes(b.key));
  const parts = nonElem.map((b) => `${STAT_LABEL[b.key]} +${b.value}%`);
  if (elem.length === WEAPON_ELEM_KEYS.length && elem.every((b) => b.value === elem[0].value)) {
    parts.push(`속성 피해 +${elem[0].value}%`);
  } else {
    parts.push(...elem.map((b) => `${STAT_LABEL[b.key]} +${b.value}%`));
  }
  return parts.join(" · ");
}

export function BuildEditor({
  reso, build, weaponById, echoById, setByName, config, slot, t, onChange, onPick, onClose,
}: {
  reso: CodexResonator;
  build: ResonatorBuild;
  weaponById: Map<string, CodexWeapon>;
  echoById: Map<string, CodexEcho>;
  setByName: Map<string, SonataSet>;
  config: GameConfig | null;
  slot: number;
  t: ReturnType<typeof useLanguage>["t"];
  onChange: (fn: (b: ResonatorBuild) => ResonatorBuild) => void;
  onPick: (p: { kind: "weapon" | "echo"; slot: number; echoIdx?: number }) => void;
  onClose: () => void;
}) {
  const weapon = build.weaponId ? weaponById.get(build.weaponId) ?? null : null;
  const active = activeSetBonuses(build, (id) => echoById.get(id)?.sonata ?? [], setByName);
  const wb = weaponBuffs(weapon, build.weaponRank); // { always, conditional, boost }
  // 무기 조건부 버프(풀 업타임)는 제거됨 — 상시(always-on) 패시브만 스탯에 반영한다.
  const stats = computeStats(reso, weapon, build, config, [...(active?.bonuses ?? []), ...wb.always]);
  const cost = buildCost(build);
  const costBudget = config?.costBudget ?? 12;
  const setEcho = (idx: number, fn: (e: NonNullable<ResonatorBuild["echoes"][number]>) => ResonatorBuild["echoes"][number]) =>
    onChange((b) => ({ ...b, echoes: b.echoes.map((e, j) => (j === idx && e ? fn(e) : e)) }));

  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={img(reso.image)} alt="" className={`h-10 w-10 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${ring(reso.rarity)}`} />
        <div>
          <div className="text-base font-semibold text-[var(--fg)]">{reso.name}</div>
          <div className="text-xs text-[var(--muted)]">{reso.rarity}★ · {reso.element} · {t.roles[reso.role]}</div>
        </div>
        <button type="button" onClick={onClose} className="ml-auto grid h-8 w-8 place-items-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]" aria-label="닫기">✕</button>
      </div>

      {/* character level */}
      <label className="grid gap-1">
        <span className="flex justify-between text-xs text-[var(--muted)]"><span>캐릭터 레벨</span><span className="text-[var(--fg)]">Lv.{build.level}</span></span>
        <input type="range" min={1} max={90} value={build.level} onChange={(e) => onChange((b) => ({ ...b, level: Number(e.target.value) }))} className="w-full accent-[var(--accent)]" />
      </label>

      {/* skill levels — 스킬별 배율 레벨(이전엔 서버에서 Lv.10 고정). 피해가 있는 레벨업 스킬만 노출 */}
      {(() => {
        const levelable = reso.skills
          .map((s, i) => ({ s, i, max: Math.max(1, ...(s.damage ?? []).map((d) => d.rates.length)) }))
          .filter((x) => x.max > 1);
        if (!levelable.length) return null;
        const lvOf = (i: number, max: number) => build.skillLevels?.[i] ?? Math.min(10, max);
        const setLv = (i: number, v: number) => onChange((b) => ({ ...b, skillLevels: { ...(b.skillLevels ?? {}), [i]: v } }));
        return (
          <div>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-semibold text-[var(--fg)]">스킬 레벨</span>
              <button type="button" onClick={() => onChange((b) => ({ ...b, skillLevels: {} }))} className="text-[11px] text-[var(--accent)] hover:underline">전체 Lv.10</button>
            </div>
            <div className="grid gap-1.5">
              {levelable.map(({ s, i, max }) => (
                <label key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-20 shrink-0 truncate text-[var(--muted)]" title={s.SkillName ?? ""}>{s.SkillType || s.SkillName || `스킬 ${i + 1}`}</span>
                  <input type="range" min={1} max={Math.min(10, max)} value={lvOf(i, max)} onChange={(e) => setLv(i, Number(e.target.value))} className="min-w-0 flex-1 accent-[var(--accent)]" />
                  <span className="w-10 shrink-0 text-right font-medium text-[var(--fg)]">Lv.{lvOf(i, max)}</span>
                </label>
              ))}
            </div>
          </div>
        );
      })()}

      {/* 공명 사슬 (S0-S6) — 보유 시퀀스 단계. 서버가 S1..seq 노드 효과를 딜에 반영(datamine 파라미터 실측 기반, 메커니즘/조건부는 미반영 표기) */}
      {(() => {
        const chain = reso.resonance_chain ?? [];
        if (!chain.length) return null;
        const seq = build.sequence ?? 0;
        const setSeq = (v: number) => onChange((b) => ({ ...b, sequence: v }));
        return (
          <div>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-semibold text-[var(--fg)]">공명 사슬</span>
              <span className="text-[11px] text-[var(--muted)]">S{seq} · 딜 반영</span>
            </div>
            <div className="flex gap-1">
              {[0, 1, 2, 3, 4, 5, 6].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setSeq(n)}
                  className={`h-7 flex-1 rounded text-xs font-semibold transition-colors ${seq === n ? "bg-[var(--accent)] text-white" : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--fg)]"}`}
                >
                  S{n}
                </button>
              ))}
            </div>
            {seq > 0 ? (
              <ol className="mt-2 grid gap-1">
                {chain.slice(0, seq).map((node, i) => (
                  <li key={i} className="text-[11px] leading-5 text-[var(--fg-soft)]">
                    <span className="mr-1 font-semibold text-[var(--accent)]">S{i + 1}</span>
                    {node.NodeName || node.AttributesDescription || ""}
                  </li>
                ))}
              </ol>
            ) : null}
          </div>
        );
      })()}

      {/* weapon */}
      <div className="rounded-md border border-[var(--line)] bg-[var(--surface-2)] p-3">
        {weapon ? (
          <>
            <div className="flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={img(weapon.icon)} alt="" className="h-9 w-9 rounded object-contain" />
              <div className="min-w-0 flex-1"><div className="truncate text-sm font-medium text-[var(--fg)]">{weapon.name_ko}</div><div className="text-xs text-[var(--muted)]">{weapon.rarity}★ · {weapon.weapon_type_ko}</div></div>
              <button type="button" onClick={() => onPick({ kind: "weapon", slot })} className="text-xs text-[var(--accent)] hover:underline">교체</button>
            </div>
            <label className="mt-2 grid gap-1">
              <span className="flex justify-between text-xs text-[var(--muted)]"><span>무기 레벨</span><span className="text-[var(--fg)]">Lv.{build.weaponLevel}</span></span>
              <input type="range" min={1} max={90} value={build.weaponLevel} onChange={(e) => onChange((b) => ({ ...b, weaponLevel: Number(e.target.value) }))} className="w-full accent-[var(--accent)]" />
            </label>
            <label className="mt-2 grid gap-1">
              <span className="flex justify-between text-xs text-[var(--muted)]"><span>정제</span><span className="text-[var(--fg)]">R{build.weaponRank}</span></span>
              <input type="range" min={1} max={5} value={build.weaponRank} onChange={(e) => onChange((b) => ({ ...b, weaponRank: Number(e.target.value) }))} className="w-full accent-[var(--accent)]" />
            </label>
            {wb.always.length ? (
              <p className="mt-2 inline-flex items-center gap-1 rounded bg-[var(--accent-soft,var(--surface-2))] px-2 py-0.5 text-[11px] font-medium text-[var(--accent)]">
                패시브 · {weaponBuffSummary(wb.always)}
              </p>
            ) : null}
            {weapon.desc ? (
              <p className="mt-2 text-[11px] leading-5 text-[var(--fg-soft)]">{weaponDescAtRank(weapon.desc, build.weaponRank)}</p>
            ) : null}
          </>
        ) : (
          <button type="button" onClick={() => onPick({ kind: "weapon", slot })} className="w-full py-2 text-sm text-[var(--accent)]">+ 무기 선택</button>
        )}
      </div>

      {/* echoes */}
      <div>
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-semibold text-[var(--fg)]">에코</span>
          <span className={cost > costBudget ? "text-[var(--gold)]" : "text-[var(--muted)]"}>코스트 {cost}/{costBudget}</span>
        </div>
        <div className="grid gap-2">
          {build.echoes.map((e, idx) => {
            const codex = e ? echoById.get(e.echoId) : null;
            return e ? (
              <div key={idx} className="rounded-md border border-[var(--line)] bg-[var(--surface-2)] p-2.5">
                <div className="flex items-center gap-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img(codex?.icon)} alt="" className="h-8 w-8 rounded object-contain" />
                  <div className="min-w-0 flex-1"><div className="truncate text-xs font-medium text-[var(--fg)]">{codex?.name_ko ?? "에코"}</div><div className="text-[11px] text-[var(--muted)]">{e.cost} 코스트</div></div>
                  <button type="button" onClick={() => onPick({ kind: "echo", slot, echoIdx: idx })} className="text-[11px] text-[var(--accent)] hover:underline">교체</button>
                  <button type="button" onClick={() => onChange((b) => ({ ...b, echoes: b.echoes.map((x, j) => (j === idx ? null : x)) }))} className="text-[11px] text-[var(--muted)] hover:text-[var(--fg)]">제거</button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                  <label className="flex items-center gap-1">등급
                    <select value={e.grade} onChange={(ev) => setEcho(idx, (x) => ({ ...x, grade: Number(ev.target.value) }))} className="rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-[var(--fg)]">
                      {[5, 4, 3, 2, 1].map((g) => <option key={g} value={g}>{g}★</option>)}
                    </select>
                  </label>
                  <label className="flex items-center gap-1">메인
                    <select value={e.main} onChange={(ev) => setEcho(idx, (x) => ({ ...x, main: ev.target.value as StatKey }))} className="rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-[var(--fg)]">
                      {(config ? echoMainOptions(config, e.cost) : []).map((o) => <option key={o.key} value={o.key}>{STAT_LABEL[o.key]}</option>)}
                    </select>
                  </label>
                  <label className="flex flex-1 items-center gap-1">Lv.{e.level}
                    <input type="range" min={0} max={25} value={e.level} onChange={(ev) => setEcho(idx, (x) => ({ ...x, level: Number(ev.target.value) }))} className="w-full accent-[var(--accent)]" />
                  </label>
                </div>
                {/* sub-stats (추가옵션) */}
                <div className="mt-2 grid gap-1">
                  {e.subs.map((s, si) => (
                    <div key={si} className="flex items-center gap-1.5 text-[11px]">
                      <select value={s.key} onChange={(ev) => setEcho(idx, (x) => ({ ...x, subs: x.subs.map((y, k) => (k === si ? { key: ev.target.value as StatKey, value: config ? subMax(config, ev.target.value as StatKey) : 0 } : y)) }))} className="flex-1 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-[var(--fg)]">
                        {(config?.sub ?? []).map((o) => <option key={o.key} value={o.key}>{STAT_LABEL[o.key]}</option>)}
                      </select>
                      <input type="number" step="0.1" value={s.value} onChange={(ev) => setEcho(idx, (x) => ({ ...x, subs: x.subs.map((y, k) => (k === si ? { ...y, value: Number(ev.target.value) } : y)) }))} className="w-16 rounded border border-[var(--line-2)] bg-[var(--surface)] px-1 py-0.5 text-right text-[var(--fg)]" />
                      <button type="button" onClick={() => setEcho(idx, (x) => ({ ...x, subs: x.subs.filter((_, k) => k !== si) }))} className="text-[var(--muted)] hover:text-[var(--fg)]">✕</button>
                    </div>
                  ))}
                  {e.subs.length < (config ? subSlots(config, e.grade) : 0) ? (
                    <button type="button" onClick={() => setEcho(idx, (x) => ({ ...x, subs: [...x.subs, { key: "crit", value: config ? subMax(config, "crit") : 0 }] }))} className="justify-self-start text-[11px] text-[var(--accent)] hover:underline">+ 추가옵션</button>
                  ) : null}
                </div>
              </div>
            ) : (
              <button key={idx} type="button" onClick={() => onPick({ kind: "echo", slot, echoIdx: idx })} className="rounded-md border border-dashed border-[var(--line-2)] py-2 text-xs text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--accent)]">+ 에코 {idx + 1}</button>
            );
          })}
        </div>
      </div>

      {/* active sonata set effect */}
      {active ? (
        <div className="rounded-md border border-[var(--line)] bg-[var(--surface-2)] p-2.5 text-xs">
          <span className="font-semibold text-[var(--fg)]">세트 효과</span>{" "}
          <span className="text-[var(--fg-soft)]">{active.sets.map((s) => `${s.name} ${s.count >= 5 ? "5세트" : "2세트"}`).join(" + ")}</span>
          {active.bonuses.length ? (
            <span className="text-[var(--accent)]"> · {active.bonuses.map((b) => `${STAT_LABEL[b.key]} +${b.value}%`).join(", ")}</span>
          ) : null}
        </div>
      ) : null}

      {/* final stats */}
      <div>
        <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">최종 스탯</h4>
        <dl className="grid grid-cols-2 gap-1.5 text-sm">
          {PANEL_KEYS.map((k) => (
            <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2.5 py-1.5"><dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt><dd className="font-medium text-[var(--fg)]">{fmtStat(k, stats[k])}</dd></div>
          ))}
          {(Object.keys(STAT_LABEL) as StatKey[]).filter((k) => !PANEL_KEYS.includes(k) && Math.abs(stats[k]) > 0.05).map((k) => (
            <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2.5 py-1.5"><dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt><dd className="font-medium text-[var(--fg)]">{fmtStat(k, stats[k])}</dd></div>
          ))}
        </dl>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
export function PickerModal({
  kind, resos, weapons, echoes, onChoose, onClose, t,
}: {
  kind: "resonator" | "weapon" | "echo";
  resos: CodexResonator[];
  weapons: CodexWeapon[];
  echoes: CodexEcho[];
  onChoose: (r: CodexResonator | CodexWeapon | CodexEcho) => void;
  onClose: () => void;
  t: ReturnType<typeof useLanguage>["t"];
}) {
  const [q, setQ] = useState("");
  const items: { id: string | number; name: string; image?: string | null; rarity: number; hint?: string; raw: CodexResonator | CodexWeapon | CodexEcho }[] =
    kind === "resonator"
      ? resos.map((r) => ({ id: r.id, name: r.name, image: r.image, rarity: r.rarity, hint: t.roles[r.role], raw: r }))
      : kind === "weapon"
        ? weapons.map((w) => ({ id: w.id, name: w.name_ko, image: w.icon, rarity: w.rarity, hint: w.weapon_type_ko ?? "", raw: w }))
        : echoes.map((e) => ({ id: e.id, name: e.name_ko, image: e.icon, rarity: e.rarity, hint: `${e.cost}코스트`, raw: e }));
  const filtered = q ? items.filter((i) => i.name.includes(q)) : items;
  const label = kind === "resonator" ? "공명자" : kind === "weapon" ? "무기" : "에코";

  return (
    <Portal>
      <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/60 p-4" role="dialog" aria-modal="true" onClick={onClose}>
        <div className="relative flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--surface)] shadow-xl" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-2 border-b border-[var(--line)] p-3">
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder={`${label} 검색`} className="min-w-0 flex-1 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--fg)] outline-none" />
            <button type="button" onClick={onClose} className="grid h-8 w-8 place-items-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]" aria-label="닫기">✕</button>
          </div>
          <div className="grid grid-cols-3 gap-2 overflow-y-auto p-3 sm:grid-cols-4 md:grid-cols-6">
            {filtered.map((it) => (
              <button key={it.id} type="button" onClick={() => onChoose(it.raw)} title={it.name} className="flex flex-col items-center gap-1 rounded-md border border-[var(--line)] p-2 text-center transition hover:border-[var(--accent)] hover:bg-[var(--surface-2)]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={img(it.image)} alt="" className={`h-12 w-12 rounded-md bg-[var(--surface-2)] object-contain ring-2 ${ring(it.rarity)}`} />
                <span className="line-clamp-1 text-[11px] text-[var(--fg-soft)]">{it.name}</span>
              </button>
            ))}
            {filtered.length === 0 ? <p className="col-span-full py-8 text-center text-sm text-[var(--muted)]">결과가 없습니다.</p> : null}
          </div>
        </div>
      </div>
    </Portal>
  );
}
