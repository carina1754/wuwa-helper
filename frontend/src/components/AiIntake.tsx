"use client";

import { useMemo, useState } from "react";
import { extractVision } from "@/lib/api";
import { mediaUrl } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { AiProfile, CodexResonator } from "@/lib/types";

const PLAY_STYLES: { value: string; labelKey: "highBurst" | "easyAuto" | "sustain" | "support" }[] = [
  { value: "고점 딜(뽕맛)", labelKey: "highBurst" },
  { value: "편하게 자동", labelKey: "easyAuto" },
  { value: "지속 딜/생존", labelKey: "sustain" },
  { value: "서포트/힐 위주", labelKey: "support" },
];

/** 인트로 화면: 연각 레벨 · 희망 캐릭터 칩 · 플레이스타일 · 자유 메모 · (선택) 스크린샷.
 * 스크린샷 없이도 제출 가능. 제출 시 프로필과 첫 메시지를 상위로 전달. */
export function AiIntake({
  resonators,
  onStart,
}: {
  resonators: CodexResonator[];
  onStart: (profile: AiProfile, firstMessage: string) => void;
}) {
  const { t } = useLanguage();
  const [desired, setDesired] = useState<string[]>([]);
  const [owned, setOwned] = useState<string[]>([]);
  const [charQuery, setCharQuery] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [playStyle, setPlayStyle] = useState<string>("");
  const [customStyle, setCustomStyle] = useState("");
  const [note, setNote] = useState("");
  const [visionStatus, setVisionStatus] = useState("");
  const [visionBusy, setVisionBusy] = useState(false);

  const byName = useMemo(() => new Map(resonators.map((r) => [r.name, r])), [resonators]);
  const filtered = useMemo(
    () => (charQuery.trim() ? resonators.filter((r) => r.name.includes(charQuery.trim())) : resonators),
    [resonators, charQuery],
  );

  /** 아이콘 탭으로 추가/제거 토글 — 입력·Enter 불필요(모바일 우선). */
  const toggleDesired = (name: string) => {
    setDesired((prev) => (prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]));
  };

  const handleScreenshot = async (file: File | null) => {
    if (!file) return;
    setVisionBusy(true);
    setVisionStatus(t.aiIntake.analyzingScreenshot);
    try {
      const result = await extractVision(file);
      const name = result.snapshot.character_name?.trim();
      if (name && !owned.includes(name)) {
        setOwned((prev) => [...prev, name]);
        setVisionStatus(`${t.aiIntake.recognized}: ${name}`);
      } else {
        setVisionStatus(t.aiIntake.notRecognized);
      }
    } catch {
      setVisionStatus(t.aiIntake.visionFailed);
    } finally {
      setVisionBusy(false);
    }
  };

  const submit = () => {
    const effectiveStyle = customStyle.trim() || playStyle; // 직접 입력이 프리셋보다 우선
    const profile: AiProfile = {
      owned_characters: owned,
      desired_characters: desired,
      play_style: effectiveStyle || null,
      note: note.trim() || null,
    };
    const parts = [
      desired.length ? `쓰고 싶은 캐릭터: ${desired.join(", ")}` : null,
      owned.length ? `보유 캐릭터: ${owned.join(", ")}` : null,
      effectiveStyle ? `플레이 스타일: ${effectiveStyle}` : null,
      note.trim() || null,
    ].filter(Boolean);
    const firstMessage = parts.length
      ? `${parts.join(" / ")}. 이 조건으로 캐릭터·무기·에코·업그레이드 순서를 추천해줘.`
      : "캐릭터·무기·에코·업그레이드 순서를 추천해줘.";
    onStart(profile, firstMessage);
  };

  return (
    <div className="grid max-w-2xl gap-5">
      <div>
        <h2 className="text-lg font-semibold">{t.aiIntake.heading}</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-neutral-400">
          {t.aiIntake.description}
        </p>
      </div>

      <div className="grid gap-1">
        <span className="text-sm font-medium">{t.aiIntake.desiredCharacters}</span>
        <div className="relative">
          <button
            type="button"
            onClick={() => setPickerOpen((o) => !o)}
            className="flex w-full items-center justify-between rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            <span className={desired.length ? "" : "text-slate-400 dark:text-neutral-500"}>
              {desired.length ? `${desired.length}${t.aiIntake.selectedSuffix}` : t.aiIntake.selectPrompt}
            </span>
            <span className="text-slate-400 dark:text-neutral-500">{pickerOpen ? "▲" : "▼"}</span>
          </button>
          {pickerOpen ? (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setPickerOpen(false)} />
              <div className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-lg border border-slate-300 bg-white shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
                <div className="flex items-center gap-2 border-b border-slate-200 p-2 dark:border-neutral-800">
                  <input
                    value={charQuery}
                    onChange={(e) => setCharQuery(e.target.value)}
                    placeholder={t.aiIntake.nameSearch}
                    className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-neutral-700 dark:bg-neutral-950"
                  />
                  <button type="button" onClick={() => setPickerOpen(false)} className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white">
                    {t.aiIntake.done}
                  </button>
                </div>
                <div className="grid max-h-72 grid-cols-4 gap-1 overflow-y-auto p-2 sm:grid-cols-6">
                  {filtered.map((r) => {
                    const on = desired.includes(r.name);
                    return (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => toggleDesired(r.name)}
                        title={r.name}
                        className={`flex flex-col items-center gap-1 rounded-md border p-1.5 text-center transition ${
                          on
                            ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50"
                            : "border-transparent hover:border-slate-300 hover:bg-slate-50 dark:hover:border-neutral-700 dark:hover:bg-neutral-800"
                        }`}
                      >
                        <span className="relative">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={mediaUrl(r.image)} alt="" className="h-11 w-11 rounded-md bg-slate-100 object-cover dark:bg-neutral-800" />
                          {on ? (
                            <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-indigo-600 text-[10px] text-white">✓</span>
                          ) : null}
                        </span>
                        <span className="line-clamp-1 text-[11px] text-slate-700 dark:text-neutral-300">{r.name}</span>
                      </button>
                    );
                  })}
                  {filtered.length === 0 ? (
                    <p className="col-span-full py-6 text-center text-sm text-slate-400 dark:text-neutral-500">{t.aiIntake.noResults}</p>
                  ) : null}
                </div>
              </div>
            </>
          ) : null}
        </div>
        {desired.length > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {desired.map((n) => {
              const r = byName.get(n);
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => setDesired(desired.filter((x) => x !== n))}
                  className="flex items-center gap-1.5 rounded-full bg-indigo-100 py-1 pl-1 pr-2.5 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                >
                  {r?.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={mediaUrl(r.image)} alt="" className="h-5 w-5 rounded-full object-cover" />
                  ) : null}
                  {n} ✕
                </button>
              );
            })}
          </div>
        ) : null}
      </div>

      <div className="grid gap-1">
        <span className="text-sm font-medium">{t.aiIntake.playStyle}</span>
        <div className="flex flex-wrap gap-1.5">
          {PLAY_STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => {
                setPlayStyle(playStyle === s.value ? "" : s.value);
                setCustomStyle("");
              }}
              className={
                playStyle === s.value && !customStyle.trim()
                  ? "rounded-full bg-indigo-600 px-3 py-1 text-xs text-white"
                  : "rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700 dark:bg-neutral-800 dark:text-neutral-300"
              }
            >
              {t.aiIntake[s.labelKey]}
            </button>
          ))}
        </div>
        <input
          value={customStyle}
          onChange={(e) => setCustomStyle(e.target.value)}
          placeholder={t.aiIntake.customStylePlaceholder}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
      </div>

      <label className="grid gap-1">
        <span className="text-sm font-medium">{t.aiIntake.note}</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder={t.aiIntake.notePlaceholder}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
      </label>

      <div className="grid gap-1.5">
        <span className="text-sm font-medium">{t.aiIntake.screenshotAdd}</span>
        <label
          className={`group flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm transition hover:border-indigo-400 hover:bg-indigo-50/60 dark:border-neutral-700 dark:bg-neutral-900 dark:hover:border-indigo-500 dark:hover:bg-indigo-950/40 ${
            visionBusy ? "pointer-events-none opacity-60" : ""
          }`}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-indigo-100 text-indigo-600 transition group-hover:bg-indigo-600 group-hover:text-white dark:bg-indigo-950 dark:text-indigo-300">
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
            <span className="font-medium text-slate-700 dark:text-neutral-200">
              {visionBusy ? t.aiIntake.analyzing : t.aiIntake.dropImage}
            </span>
            <span className="text-xs text-slate-400 dark:text-neutral-500">{t.aiIntake.screenshotHint}</span>
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
        {visionStatus ? <span className="text-xs text-slate-500 dark:text-neutral-400">{visionStatus}</span> : null}
        {owned.length > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {owned.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setOwned(owned.filter((x) => x !== n))}
                className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
              >
                {n} ✕
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <button
        type="button"
        onClick={submit}
        className="justify-self-start rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
      >
        {t.aiIntake.startBuild}
      </button>
    </div>
  );
}

export default AiIntake;
