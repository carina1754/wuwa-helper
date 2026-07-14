"use client";

import { useEffect, useMemo, useState } from "react";
import { deleteRecommendation, getCodexEchoes, getCodexResonators, getCodexWeapons, getGameConfig, getRecommendations, getSonataSets } from "@/lib/api";
import { RecommendationCard, type NameMaps } from "./RecommendationCard";
import type { GameConfig } from "@/lib/build";
import { computePartyDamage } from "@/lib/partyDamage";
import type { AiRecommendationRecord, CodexResonator, CodexWeapon } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

const EMPTY_NAMES: NameMaps = {
  resonator: new Map(),
  weapon: new Map(),
  echo: new Map(),
  sonata: new Map(),
};

const DATE_LOCALES: Record<string, string> = {
  ko: "ko-KR",
  ja: "ja-JP",
  zhHans: "zh-CN",
  en: "en-US",
};

/** 기록 탭: 확정 저장된 AI 추천을 아이콘 카드로 재열람. */
export function AiHistory() {
  const { t, language } = useLanguage();

  const [records, setRecords] = useState<AiRecommendationRecord[]>([]);
  const [names, setNames] = useState<NameMaps>(EMPTY_NAMES);
  const [resonators, setResonators] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [gameConfig, setGameConfig] = useState<GameConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (deletingId) return;
    if (!window.confirm(t.aiHistory.confirmDelete)) return;
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
  }, []);

  if (loading) {
    return <p className="text-sm text-slate-500 dark:text-neutral-400">{t.aiHistory.loading}</p>;
  }

  if (records.length === 0) {
    return (
      <div className="grid gap-1">
        <h2 className="text-lg font-semibold">{t.aiHistory.title}</h2>
        <p className="text-sm text-slate-500 dark:text-neutral-400">
          {t.aiHistory.emptyBody}
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <h2 className="text-lg font-semibold">{t.aiHistory.title}</h2>
      {records.map((rec) => (
        <div key={rec.id} className="grid gap-1">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-400">{new Date(rec.created_at).toLocaleString(DATE_LOCALES[language] ?? "ko-KR")}</p>
            <button
              type="button"
              onClick={() => handleDelete(rec.id)}
              disabled={deletingId === rec.id}
              className="rounded-md px-2 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-950 dark:hover:text-red-400"
            >
              {deletingId === rec.id ? t.aiHistory.deleting : t.aiHistory.delete}
            </button>
          </div>
          <RecommendationCard
            recommendation={rec.recommendation}
            names={names}
            damage={computePartyDamage(rec.recommendation, resoById, weaponById, gameConfig)}
          />
          {rec.profile?.note ? (
            <details className="mt-1 text-xs text-slate-500 dark:text-neutral-400">
              <summary className="cursor-pointer select-none">{t.aiHistory.selectedBuildMemo}</summary>
              <pre className="mt-1 whitespace-pre-wrap font-sans">{rec.profile.note}</pre>
            </details>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default AiHistory;
