"use client";

import { useEffect, useMemo, useState } from "react";
import { Portal } from "./Portal";
import { getCodexEchoes, getCodexResonators, getCodexWeapons, getGameConfig } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { CodexEcho, CodexResonator, CodexWeapon } from "@/lib/types";
import {
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
} from "@/lib/build";

const PARTY_SIZE = 3;
const STORAGE_KEY = "mj:party:v2";
const PANEL_KEYS: StatKey[] = ["hp", "atk", "def", "crit", "critDmg", "energyRegen"];

function img(p?: string | null): string | undefined {
  if (!p) return undefined;
  return /^https?:\/\//.test(p) ? p : `/backend${p}`;
}
function ring(r: number): string {
  return r >= 5 ? "ring-[var(--gold)]" : "ring-[color-mix(in_srgb,var(--accent)_60%,transparent)]";
}

type Slot = { resonatorId: number | null; build: ResonatorBuild };
const newParty = (): Slot[] => Array.from({ length: PARTY_SIZE }, () => ({ resonatorId: null, build: emptyBuild() }));

export function TeamBuilder() {
  const { t } = useLanguage();
  const [resos, setResos] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [echoes, setEchoes] = useState<CodexEcho[]>([]);
  const [config, setConfig] = useState<GameConfig | null>(null);
  const [party, setParty] = useState<Slot[]>(newParty);
  const [editing, setEditing] = useState<number | null>(null);
  const [picker, setPicker] = useState<null | { kind: "resonator" | "weapon" | "echo"; slot: number; echoIdx?: number }>(null);

  useEffect(() => {
    getCodexResonators().then(setResos).catch(() => {});
    getCodexWeapons().then(setWeapons).catch(() => {});
    getCodexEchoes().then(setEchoes).catch(() => {});
    getGameConfig()
      .then((c) => setConfig((c?.echo_stats as GameConfig) ?? null))
      .catch(() => {});
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
  // one representative echo per name (encore lists id/rarity variants)
  const echoList = useMemo(() => {
    const m = new Map<string, CodexEcho>();
    for (const e of echoes) {
      const cur = m.get(e.name_ko);
      if (!cur || (e.rarity ?? 0) > (cur.rarity ?? 0)) m.set(e.name_ko, e);
    }
    return [...m.values()];
  }, [echoes]);

  const setSlot = (i: number, fn: (s: Slot) => Slot) => setParty((p) => p.map((s, j) => (j === i ? fn(s) : s)));
  const setBuild = (i: number, fn: (b: ResonatorBuild) => ResonatorBuild) => setSlot(i, (s) => ({ ...s, build: fn(s.build) }));

  const choose = (r: CodexResonator | CodexWeapon | CodexEcho) => {
    if (!picker) return;
    const { kind, slot, echoIdx } = picker;
    if (kind === "resonator") setSlot(slot, (s) => ({ ...s, resonatorId: (r as CodexResonator).id }));
    else if (kind === "weapon") setBuild(slot, (b) => ({ ...b, weaponId: (r as CodexWeapon).id }));
    else if (kind === "echo" && echoIdx != null && config)
      setBuild(slot, (b) => ({ ...b, echoes: b.echoes.map((e, j) => (j === echoIdx ? echoFromCodex(r as CodexEcho, config) : e)) }));
    setPicker(null);
  };

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-xl font-semibold text-[var(--fg)]">{t.teams.title}</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">공명자 3명의 캐릭터·무기·에코를 설정해 파티 빌드를 꾸리고 최종 스탯을 확인하세요.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {party.map((slot, i) => {
          const reso = slot.resonatorId != null ? resoById.get(slot.resonatorId) : null;
          const stats = reso ? computeStats(reso, slot.build.weaponId ? weaponById.get(slot.build.weaponId) ?? null : null, slot.build, config) : null;
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
function BuildEditor({
  reso, build, weaponById, echoById, config, slot, t, onChange, onPick, onClose,
}: {
  reso: CodexResonator;
  build: ResonatorBuild;
  weaponById: Map<string, CodexWeapon>;
  echoById: Map<string, CodexEcho>;
  config: GameConfig | null;
  slot: number;
  t: ReturnType<typeof useLanguage>["t"];
  onChange: (fn: (b: ResonatorBuild) => ResonatorBuild) => void;
  onPick: (p: { kind: "weapon" | "echo"; slot: number; echoIdx?: number }) => void;
  onClose: () => void;
}) {
  const weapon = build.weaponId ? weaponById.get(build.weaponId) ?? null : null;
  const stats = computeStats(reso, weapon, build, config);
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
            <div className="mt-2 flex items-center gap-1.5 text-xs">
              <span className="text-[var(--muted)]">정제</span>
              {[1, 2, 3, 4, 5].map((r) => (
                <button key={r} type="button" onClick={() => onChange((b) => ({ ...b, weaponRank: r }))} className={`h-6 w-6 rounded ${build.weaponRank === r ? "bg-[var(--accent)] text-[var(--accent-ink)]" : "bg-[var(--surface)] text-[var(--fg-soft)]"}`}>{r}</button>
              ))}
            </div>
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
function PickerModal({
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
