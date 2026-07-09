"use client";

import { useState } from "react";
import { RecommendationCard, type NameMaps } from "./RecommendationCard";
import type { PartyDamage } from "@/lib/partyDamage";
import type { AiMessage, Recommendation } from "@/lib/types";

/** 대화 메시지 리스트 + 입력창. 추천안은 해당 어시스턴트 메시지 아래 카드로 표시. */
export function AiChat({
  messages,
  latestRecommendation,
  names,
  damage,
  loading,
  onSend,
  onConfirm,
  confirming,
}: {
  messages: AiMessage[];
  latestRecommendation: Recommendation | null;
  names: NameMaps;
  damage?: PartyDamage | null;
  loading: boolean;
  onSend: (text: string) => void;
  onConfirm: () => void;
  confirming: boolean;
}) {
  const [draft, setDraft] = useState("");

  const submit = () => {
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    onSend(text);
  };

  return (
    <div className="grid gap-3">
      <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:bg-neutral-900 dark:text-neutral-400">
        답변이 최대 30초 정도 걸릴 수 있습니다.
      </p>

      <div className="grid gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] rounded-lg bg-indigo-600 px-3 py-2 text-sm text-white"
                : "mr-auto max-w-[85%] rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-900 dark:bg-neutral-800 dark:text-neutral-100"
            }
          >
            <p className="whitespace-pre-wrap">{m.content}</p>
          </div>
        ))}

        {latestRecommendation ? (
          <RecommendationCard
            recommendation={latestRecommendation}
            names={names}
            damage={damage}
            onConfirm={onConfirm}
            confirming={confirming}
          />
        ) : null}

        {loading ? (
          <div className="mr-auto flex items-center text-sm text-slate-400">
            빌드 생성 중
            <span className="ml-0.5 inline-flex">
              <span className="mj-dot">.</span>
              <span className="mj-dot">.</span>
              <span className="mj-dot">.</span>
            </span>
          </div>
        ) : null}
      </div>

      <div className="flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="예: 창리를 메인 딜러로 쓰고 싶어요"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
        />
        <button
          type="button"
          onClick={submit}
          disabled={loading || !draft.trim()}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          보내기
        </button>
      </div>
    </div>
  );
}

export default AiChat;
