"use client";

import { useEffect, useMemo, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { deleteRecommendation, getCodexEchoes, getCodexResonators, getCodexWeapons, getGameConfig, getRecommendations, getSonataSets } from "@/lib/api";
import { RecommendationCard, type NameMaps } from "./RecommendationCard";
import type { GameConfig } from "@/lib/build";
import { computePartyDamage } from "@/lib/partyDamage";
import type { AiRecommendationRecord, CodexResonator, CodexWeapon } from "@/lib/types";

const EMPTY_NAMES: NameMaps = {
  resonator: new Map(),
  weapon: new Map(),
  echo: new Map(),
  sonata: new Map(),
};

/** 기록 탭: 확정 저장된 AI 추천을 아이콘 카드로 재열람. */
export function AiHistory() {
  const { data: session, status } = useSession();
  const userId = session?.user?.email ?? null;

  const [records, setRecords] = useState<AiRecommendationRecord[]>([]);
  const [names, setNames] = useState<NameMaps>(EMPTY_NAMES);
  const [resonators, setResonators] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [gameConfig, setGameConfig] = useState<GameConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    if (!window.confirm("이 기록을 삭제할까요?")) return;
    setDeletingId(id);
    try {
      await deleteRecommendation(id);
      setRecords((prev) => prev.filter((r) => r.id !== id));
    } catch {
      /* 삭제 실패 시 목록 유지 */
    } finally {
      setDeletingId(null);
    }
  };

  const resoById = useMemo(() => new Map(resonators.map((r) => [r.id, r])), [resonators]);
  const weaponById = useMemo(() => new Map(weapons.map((w) => [w.id, w])), [weapons]);

  useEffect(() => {
    let cancelled = false;
    if (!userId) {
      setRecords([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    void (async () => {
      try {
        const [recs, res, weaponList, echoes, sonatas, config] = await Promise.all([
          getRecommendations(),
          getCodexResonators(),
          getCodexWeapons(),
          getCodexEchoes(),
          getSonataSets(),
          getGameConfig().catch(() => null),
        ]);
        if (cancelled) return;
        setRecords(recs);
        setResonators(res);
        setWeapons(weaponList);
        setGameConfig(config ? (config as unknown as GameConfig) : null);
        setNames({
          resonator: new Map(res.map((r) => [String(r.id), r.name])),
          weapon: new Map(weaponList.map((w) => [String(w.id), w.name_ko])),
          echo: new Map(echoes.map((e) => [String(e.id), e.name_ko])),
          sonata: new Map(sonatas.map((s) => [String(s.id), s.name_ko])),
        });
      } catch {
        /* 조회 실패 시 빈 목록 */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!userId) {
    return (
      <div className="grid max-w-md gap-3">
        <h2 className="text-lg font-semibold">기록</h2>
        <p className="text-sm text-slate-500 dark:text-neutral-400">
          {status === "loading" ? "로그인 상태를 확인하는 중…" : "구글 로그인하면 내 계정에 저장된 추천 기록을 볼 수 있어요."}
        </p>
        {status !== "loading" ? (
          <button
            type="button"
            onClick={() => void signIn("google", { callbackUrl: "/" })}
            className="justify-self-start rounded-md bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            구글로 로그인
          </button>
        ) : null}
      </div>
    );
  }

  if (loading) {
    return <p className="text-sm text-slate-500 dark:text-neutral-400">기록을 불러오는 중…</p>;
  }

  if (records.length === 0) {
    return (
      <div className="grid gap-1">
        <h2 className="text-lg font-semibold">기록</h2>
        <p className="text-sm text-slate-500 dark:text-neutral-400">
          아직 저장된 추천이 없어요. AI 탭에서 추천을 받고 &ldquo;이걸로 확정&rdquo;을 누르면 여기에 저장됩니다.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">기록</h2>
      {records.map((rec) => (
        <div key={rec.id} className="grid gap-1">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">{new Date(rec.created_at).toLocaleString("ko-KR")}</p>
            <button
              type="button"
              onClick={() => handleDelete(rec.id)}
              disabled={deletingId === rec.id}
              className="rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-950 dark:hover:text-red-400"
            >
              {deletingId === rec.id ? "삭제 중…" : "삭제"}
            </button>
          </div>
          <RecommendationCard
            recommendation={rec.recommendation}
            names={names}
            damage={computePartyDamage(rec.recommendation, resoById, weaponById, gameConfig)}
          />
          {rec.profile?.note ? (
            <details className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
              <summary className="cursor-pointer select-none">선택한 구성 / 메모</summary>
              <pre className="mt-1 whitespace-pre-wrap font-sans">{rec.profile.note}</pre>
            </details>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default AiHistory;
