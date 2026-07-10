"use client";

import { useEffect, useMemo, useState } from "react";
import { extractVision, getCodexResonators, getCodexWeapons, snapshotDamage } from "@/lib/api";
import { emptySnapshot } from "@/lib/constants";
import { fmtStat, STAT_LABEL, type StatKey } from "@/lib/build";
import type { CharacterSnapshot, CodexResonator, CodexWeapon, EchoItem, SnapshotDamageResult } from "@/lib/types";

/** 저장된 이미지 경로 → 백엔드 프록시. TeamBuilder.img와 동일 규칙. */
function img(p?: string | null): string | undefined {
  if (!p) return undefined;
  return /^https?:\/\//.test(p) ? p : `/backend${p}`;
}
function ring(r?: number | null): string {
  return (r ?? 0) >= 5 ? "ring-[var(--gold)]" : "ring-[color-mix(in_srgb,var(--accent)_60%,transparent)]";
}

// 결과 스탯에서 항상 보여줄 핵심 + 그 외 0이 아닌 값은 동적 표시
const CORE_STATS: StatKey[] = ["hp", "atk", "def", "crit", "critDmg", "energyRegen"];

/** 스샷/수동 스냅샷 → 서버 엔진으로 "내 실제 빌드" 절대 피해를 계산하는 탭.
 * 팀 시뮬(상대 비교)과 달리 실제 측정된 에코 부가옵션을 그대로 쓰는 게 차별점. */
export function SnapshotDamage() {
  const [snapshot, setSnapshot] = useState<CharacterSnapshot | null>(null);
  const [result, setResult] = useState<SnapshotDamageResult | null>(null);
  const [visionBusy, setVisionBusy] = useState(false);
  const [calcBusy, setCalcBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [resos, setResos] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);

  useEffect(() => {
    getCodexResonators().then(setResos).catch(() => {});
    getCodexWeapons().then(setWeapons).catch(() => {});
  }, []);

  const resoNames = useMemo(() => resos.map((r) => r.name).filter(Boolean), [resos]);
  const weaponNames = useMemo(() => weapons.map((w) => w.name_ko).filter(Boolean), [weapons]);
  const resoById = useMemo(() => new Map(resos.map((r) => [Number(r.id), r])), [resos]);

  const handleScreenshot = async (file: File | null) => {
    if (!file) return;
    setVisionBusy(true);
    setError("");
    setStatus("스크린샷 분석 중…");
    try {
      const res = await extractVision(file);
      setSnapshot(res.snapshot);
      setResult(null);
      const warn = [...(res.uncertain_fields ?? []), ...(res.warnings ?? [])];
      setStatus(
        res.snapshot.character_name
          ? `인식됨: ${res.snapshot.character_name}${warn.length ? ` · 확인 필요 ${warn.length}건 (아래에서 수정 가능)` : ""}`
          : "캐릭터를 특정하지 못했어요. 아래에서 직접 입력해 주세요.",
      );
    } catch {
      setError("스크린샷 분석에 실패했어요. '빈 양식으로 입력'으로 수동 입력할 수 있어요.");
    } finally {
      setVisionBusy(false);
    }
  };

  const calculate = async () => {
    if (!snapshot) return;
    setCalcBusy(true);
    setError("");
    try {
      const res = await snapshotDamage({ snapshot });
      setResult(res);
    } catch (e) {
      setResult(null);
      setError(e instanceof Error && e.message ? e.message : "계산에 실패했어요. 캐릭터·무기 이름이 정확한지 확인해 주세요.");
    } finally {
      setCalcBusy(false);
    }
  };

  const patch = (fn: (s: CharacterSnapshot) => CharacterSnapshot) => setSnapshot((s) => (s ? fn(s) : s));
  const setEcho = (i: number, fn: (e: EchoItem) => EchoItem) =>
    patch((s) => ({ ...s, echoes: s.echoes.map((e, j) => (j === i ? fn(e) : e)) }));

  const inputCls =
    "w-full rounded-md border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--fg)] outline-none focus:border-[var(--accent)]";
  const smallInputCls =
    "w-full rounded border border-[var(--line)] bg-[var(--surface-2)] px-2 py-1 text-xs text-[var(--fg)] outline-none focus:border-[var(--accent)]";

  const reso = result ? resoById.get(Number(result.reso_id)) : undefined;
  const shownStats = result
    ? [
        ...CORE_STATS.filter((k) => k in result.stats),
        ...(Object.keys(result.stats) as StatKey[]).filter(
          (k) => !CORE_STATS.includes(k) && k in STAT_LABEL && Math.abs(result.stats[k] ?? 0) > 0.05,
        ),
      ]
    : [];

  return (
    <div className="grid gap-5">
      <div>
        <h2 className="text-lg font-semibold text-[var(--fg)]">내 실제 빌드 절대 피해</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          캐릭터 정보 스크린샷을 올리면 실제 측정된 에코 부가옵션을 그대로 반영해 절대 피해를 계산합니다. 팀 시뮬의 기본값 상대 비교와 달리, 이
          수치는 당신 계정의 실측값입니다.
        </p>
      </div>

      {/* 업로드 */}
      <div className="grid gap-2">
        <label
          className={`group flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-[var(--line)] bg-[var(--surface-2)] px-4 py-3 text-sm transition hover:border-[var(--accent)] ${
            visionBusy ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-[var(--surface)] text-[var(--accent)]">
            {visionBusy ? (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
              </svg>
            )}
          </span>
          <span className="grid">
            <span className="font-medium text-[var(--fg)]">{visionBusy ? "분석 중…" : "캐릭터 정보 스크린샷 선택 또는 끌어다 놓기"}</span>
            <span className="text-xs text-[var(--muted)]">스탯·무기·에코가 보이는 캐릭터 화면 (PNG·JPG)</span>
          </span>
          <input
            type="file"
            accept="image/*"
            disabled={visionBusy}
            onChange={(e) => {
              void handleScreenshot(e.target.files?.[0] ?? null);
              e.target.value = "";
            }}
            className="sr-only"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => {
              setSnapshot(emptySnapshot());
              setResult(null);
              setError("");
              setStatus("빈 양식에 직접 입력하세요.");
            }}
            className="text-xs text-[var(--muted)] underline underline-offset-2 hover:text-[var(--fg)]"
          >
            빈 양식으로 직접 입력
          </button>
          {status ? <span className="text-xs text-[var(--fg-soft)]">{status}</span> : null}
        </div>
      </div>

      {/* 편집 폼 */}
      {snapshot ? (
        <div className="grid gap-4 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1">
              <span className="text-xs font-medium text-[var(--muted)]">캐릭터</span>
              <input
                list="snap-reso-list"
                value={snapshot.character_name ?? ""}
                onChange={(e) => patch((s) => ({ ...s, character_name: e.target.value }))}
                placeholder="예: 창리"
                className={inputCls}
              />
            </label>
            <label className="grid gap-1">
              <span className="text-xs font-medium text-[var(--muted)]">무기</span>
              <input
                list="snap-weapon-list"
                value={snapshot.weapon?.name ?? ""}
                onChange={(e) => patch((s) => ({ ...s, weapon: { ...(s.weapon ?? {}), name: e.target.value } }))}
                placeholder="예: 시대의 등불"
                className={inputCls}
              />
            </label>
          </div>
          <datalist id="snap-reso-list">
            {resoNames.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>
          <datalist id="snap-weapon-list">
            {weaponNames.map((n) => (
              <option key={n} value={n} />
            ))}
          </datalist>

          <div className="grid gap-3">
            {snapshot.echoes.map((echo, i) => (
              <div key={i} className="grid gap-2 rounded-md border border-[var(--line)] bg-[var(--surface-2)] p-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-[var(--fg-soft)]">에코 {i + 1}</span>
                  <span className="text-[11px] text-[var(--muted)]">코스트 {echo.cost ?? "–"} · Lv.{echo.level ?? "–"}</span>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  <input
                    value={echo.set_name ?? ""}
                    onChange={(e) => setEcho(i, (x) => ({ ...x, set_name: e.target.value }))}
                    placeholder="소나타(세트) 이름"
                    className={smallInputCls}
                  />
                  <input
                    value={echo.main_stat ?? ""}
                    onChange={(e) => setEcho(i, (x) => ({ ...x, main_stat: e.target.value }))}
                    placeholder="메인 스탯"
                    className={smallInputCls}
                  />
                </div>
                <div className="grid gap-1.5">
                  {echo.sub_stats.map((sub, j) => (
                    <div key={j} className="flex gap-2">
                      <input
                        value={sub.name ?? ""}
                        onChange={(e) =>
                          setEcho(i, (x) => ({ ...x, sub_stats: x.sub_stats.map((s, k) => (k === j ? { ...s, name: e.target.value } : s)) }))
                        }
                        placeholder="부가옵션"
                        className={smallInputCls}
                      />
                      <input
                        value={sub.value ?? ""}
                        onChange={(e) =>
                          setEcho(i, (x) => ({ ...x, sub_stats: x.sub_stats.map((s, k) => (k === j ? { ...s, value: e.target.value } : s)) }))
                        }
                        placeholder="값 (예: 8.4% / 30)"
                        className={smallInputCls}
                      />
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setEcho(i, (x) => ({ ...x, sub_stats: [...x.sub_stats, { name: "", value: "" }] }))}
                    className="justify-self-start text-[11px] text-[var(--muted)] hover:text-[var(--fg)]"
                  >
                    + 부가옵션 추가
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 계산 */}
      {snapshot ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={calculate}
            disabled={calcBusy || !snapshot.character_name}
            className="rounded-md bg-[var(--accent)] px-5 py-2 text-sm font-semibold text-[var(--accent-ink)] hover:opacity-90 disabled:opacity-50"
          >
            {calcBusy ? "계산 중…" : "내 빌드로 절대 피해 계산"}
          </button>
          <span className="text-xs text-[var(--muted)]">스킬 Lv.10 기준</span>
          {error ? <span className="text-xs text-[var(--danger,#e5484d)]">{error}</span> : null}
        </div>
      ) : null}

      {/* 결과 */}
      {result ? (
        <div className="grid gap-3">
          <div className="flex items-baseline justify-between rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-3">
            <span className="text-sm font-semibold text-[var(--fg)]">내 빌드 절대 피해 (1사이클)</span>
            <span className="text-2xl font-bold tabular-nums text-[var(--accent)]">{Math.round(result.total).toLocaleString()}</span>
          </div>

          <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
            <div className="flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={img(reso?.image)} alt="" className={`h-10 w-10 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${ring(reso?.rarity)}`} />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-[var(--fg)]">{result.name ?? reso?.name ?? result.reso_id}</div>
                <div className="text-xs text-[var(--muted)]">
                  {result.element ?? reso?.element}
                  {result.set_name ? ` · ${result.set_name}` : ""} · 코스트 {result.cost}
                </div>
              </div>
            </div>

            {shownStats.length ? (
              <dl className="mt-3 grid grid-cols-2 gap-1.5 text-xs sm:grid-cols-3">
                {shownStats.map((k) => (
                  <div key={k} className="flex justify-between rounded bg-[var(--surface-2)] px-2 py-1">
                    <dt className="text-[var(--muted)]">{STAT_LABEL[k]}</dt>
                    <dd className={`font-medium tabular-nums ${CORE_STATS.includes(k) ? "text-[var(--fg)]" : "text-[var(--accent)]"}`}>{fmtStat(k, result.stats[k] ?? 0)}</dd>
                  </div>
                ))}
              </dl>
            ) : null}

            {result.skills.length ? (
              <dl className="mt-2 grid gap-1 text-sm">
                {result.skills.map((s, j) => (
                  <div key={j} className="flex items-center justify-between gap-2 rounded bg-[var(--surface-2)] px-2.5 py-1.5">
                    <dt className="min-w-0 truncate text-[var(--muted)]">
                      {s.name}
                      {s.type ? ` · ${s.type}` : ""} <span className="text-[11px]">Lv.{s.level}</span>
                    </dt>
                    <dd className="shrink-0 font-medium tabular-nums text-[var(--fg)]">{Math.round(s.dmg).toLocaleString()}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <div className="mt-2 rounded bg-[var(--surface-2)] px-2.5 py-1.5 text-xs leading-relaxed text-[#e0a04d]">
                ⚠ 이 캐릭터의 스킬 배율 데이터가 없어 개인 피해를 계산할 수 없습니다.
              </div>
            )}

            {result.unresolved.length ? (
              <div className="mt-2 rounded border border-dashed border-[var(--line)] bg-[var(--surface-2)] px-2.5 py-2 text-xs text-[var(--fg-soft)]">
                <div className="mb-1 text-[10px] uppercase tracking-wide text-[var(--muted)]">인식·매칭 실패 (추정치가 낮아질 수 있음)</div>
                <div className="leading-relaxed">{result.unresolved.join(" · ")}</div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default SnapshotDamage;
