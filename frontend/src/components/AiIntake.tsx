"use client";

import { useMemo, useState } from "react";
import { extractVision } from "@/lib/api";
import type { AiProfile, CodexResonator } from "@/lib/types";

const PLAY_STYLES = ["고점 딜(뽕맛)", "편하게 자동", "지속 딜/생존", "서포트/힐 위주"];

/** 인트로 화면: 연각 레벨 · 희망 캐릭터 칩 · 플레이스타일 · 자유 메모 · (선택) 스크린샷.
 * 스크린샷 없이도 제출 가능. 제출 시 프로필과 첫 메시지를 상위로 전달. */
export function AiIntake({
  resonators,
  onStart,
}: {
  resonators: CodexResonator[];
  onStart: (profile: AiProfile, firstMessage: string) => void;
}) {
  const [desired, setDesired] = useState<string[]>([]);
  const [owned, setOwned] = useState<string[]>([]);
  const [charQuery, setCharQuery] = useState("");
  const [playStyle, setPlayStyle] = useState<string>("");
  const [note, setNote] = useState("");
  const [visionStatus, setVisionStatus] = useState("");
  const [visionBusy, setVisionBusy] = useState(false);

  const names = useMemo(() => resonators.map((r) => r.name).filter(Boolean), [resonators]);

  const addDesired = (name: string) => {
    const clean = name.trim();
    if (!clean || desired.includes(clean)) return;
    setDesired([...desired, clean]);
    setCharQuery("");
  };

  const handleScreenshot = async (file: File | null) => {
    if (!file) return;
    setVisionBusy(true);
    setVisionStatus("스크린샷 분석 중…");
    try {
      const result = await extractVision(file);
      const name = result.snapshot.character_name?.trim();
      if (name && !owned.includes(name)) {
        setOwned((prev) => [...prev, name]);
        setVisionStatus(`인식됨: ${name}`);
      } else {
        setVisionStatus("캐릭터를 특정하지 못했어요. 직접 입력해 주세요.");
      }
    } catch {
      setVisionStatus("스크린샷 분석에 실패했어요. 스크린샷 없이 진행해도 됩니다.");
    } finally {
      setVisionBusy(false);
    }
  };

  const submit = () => {
    const profile: AiProfile = {
      owned_characters: owned,
      desired_characters: desired,
      play_style: playStyle || null,
      note: note.trim() || null,
    };
    const parts = [
      desired.length ? `쓰고 싶은 캐릭터: ${desired.join(", ")}` : null,
      owned.length ? `보유 캐릭터: ${owned.join(", ")}` : null,
      playStyle ? `플레이 스타일: ${playStyle}` : null,
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
        <h2 className="text-lg font-semibold">AI 빌딩</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-neutral-400">
          현재 상황을 알려주면 캐릭터·무기·에코·업그레이드 순서를 추천하고, 대화로 다듬어 드려요.
        </p>
      </div>

      <div className="grid gap-1">
        <span className="text-sm font-medium">사용하고 싶은 캐릭터</span>
        <input
          list="ai-resonator-list"
          value={charQuery}
          onChange={(e) => setCharQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addDesired(charQuery);
            }
          }}
          placeholder="이름 입력 후 Enter"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <datalist id="ai-resonator-list">
          {names.map((n) => (
            <option key={n} value={n} />
          ))}
        </datalist>
        {desired.length > 0 ? (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {desired.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setDesired(desired.filter((x) => x !== n))}
                className="rounded-full bg-indigo-100 px-2.5 py-1 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
              >
                {n} ✕
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="grid gap-1">
        <span className="text-sm font-medium">플레이 스타일</span>
        <div className="flex flex-wrap gap-1.5">
          {PLAY_STYLES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setPlayStyle(playStyle === s ? "" : s)}
              className={
                playStyle === s
                  ? "rounded-full bg-indigo-600 px-3 py-1 text-xs text-white"
                  : "rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-700 dark:bg-neutral-800 dark:text-neutral-300"
              }
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <label className="grid gap-1">
        <span className="text-sm font-medium">추가 메모 (선택)</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          placeholder="예: 무과금이라 4성 무기 위주로, 심층 3막 클리어가 목표"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
      </label>

      <div className="grid gap-1.5">
        <span className="text-sm font-medium">스크린샷으로 보유 캐릭터 추가 (선택)</span>
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
              {visionBusy ? "분석 중…" : "이미지 파일 선택 또는 끌어다 놓기"}
            </span>
            <span className="text-xs text-slate-400 dark:text-neutral-500">캐릭터 정보 화면 스크린샷 (PNG·JPG)</span>
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
        빌드 시작하기
      </button>
    </div>
  );
}

export default AiIntake;
