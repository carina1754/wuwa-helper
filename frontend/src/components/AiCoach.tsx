"use client";

import { useEffect, useMemo, useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { aiChat, getCodexEchoes, getCodexResonators, getCodexWeapons, getGameConfig, getSonataSets, saveRecommendation } from "@/lib/api";
import { AiChat } from "./AiChat";
import { AiIntake } from "./AiIntake";
import type { NameMaps } from "./RecommendationCard";
import type { GameConfig } from "@/lib/build";
import { computePartyDamage } from "@/lib/partyDamage";
import type { AiMessage, AiProfile, CodexResonator, CodexWeapon, Recommendation } from "@/lib/types";

const EMPTY_NAMES: NameMaps = {
  resonator: new Map(),
  weapon: new Map(),
  echo: new Map(),
  sonata: new Map(),
};

/** AI 코치 탭 컨테이너: 인트로 → 대화 → 추천 카드 → 확정 저장. */
export function AiCoach() {
  const { data: session, status } = useSession();
  const userId = session?.user?.email ?? null;

  const [resonators, setResonators] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [gameConfig, setGameConfig] = useState<GameConfig | null>(null);
  const [names, setNames] = useState<NameMaps>(EMPTY_NAMES);

  const [phase, setPhase] = useState<"intake" | "chat">("intake");
  const [profile, setProfile] = useState<AiProfile>({ owned_characters: [], desired_characters: [] });
  const [messages, setMessages] = useState<AiMessage[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [savedTitle, setSavedTitle] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [res, weaponList, echoes, sonatas, config] = await Promise.all([
          getCodexResonators(),
          getCodexWeapons(),
          getCodexEchoes(),
          getSonataSets(),
          getGameConfig().catch(() => null),
        ]);
        if (cancelled) return;
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
        /* 이름 맵 로드 실패해도 id로 대체 표시되므로 치명적이지 않음 */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const send = async (nextMessages: AiMessage[], nextProfile: AiProfile) => {
    setLoading(true);
    setError("");
    try {
      const response = await aiChat(nextMessages, nextProfile);
      setMessages([...nextMessages, { role: "assistant", content: response.reply }]);
      setRecommendation(response.recommendation ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "요청에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = (nextProfile: AiProfile, firstMessage: string) => {
    setProfile(nextProfile);
    setSavedTitle(null);
    setRecommendation(null);
    const initial: AiMessage[] = [{ role: "user", content: firstMessage }];
    setMessages(initial);
    setPhase("chat");
    void send(initial, nextProfile);
  };

  const handleSend = (text: string) => {
    const next: AiMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setRecommendation(null);
    void send(next, profile);
  };

  const handleConfirm = async () => {
    if (!recommendation) return;
    if (!userId) {
      setError("기록을 저장하려면 구글 로그인이 필요해요.");
      return;
    }
    setConfirming(true);
    setError("");
    try {
      const record = await saveRecommendation({
        user_id: userId,
        profile,
        conversation: messages,
        recommendation,
        title: recommendation.summary || "AI 추천 빌드",
      });
      setSavedTitle(record.title ?? record.recommendation.summary ?? "저장됨");
      // 저장 확인 문구를 잠깐 보여준 뒤 자동으로 처음(인트로)으로 복귀.
      window.setTimeout(() => reset(), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장에 실패했습니다.");
    } finally {
      setConfirming(false);
    }
  };

  const reset = () => {
    setPhase("intake");
    setMessages([]);
    setRecommendation(null);
    setSavedTitle(null);
    setError("");
  };

  const showNames = useMemo(() => names, [names]);

  const resoById = useMemo(() => new Map(resonators.map((r) => [r.id, r])), [resonators]);
  const weaponById = useMemo(() => new Map(weapons.map((w) => [w.id, w])), [weapons]);
  const damage = useMemo(
    () => (recommendation ? computePartyDamage(recommendation, resoById, weaponById, gameConfig) : null),
    [recommendation, resoById, weaponById, gameConfig],
  );

  if (!userId) {
    return (
      <div className="grid max-w-md gap-3">
        <h2 className="text-lg font-semibold">AI 빌딩</h2>
        <p className="text-sm text-slate-500 dark:text-neutral-400">
          {status === "loading"
            ? "로그인 상태를 확인하는 중…"
            : "AI 빌드 추천은 구글 로그인 후 이용할 수 있어요. 로그인하면 추천이 내 계정 기록으로 저장됩니다."}
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

  if (phase === "intake") {
    return <AiIntake resonators={resonators} onStart={handleStart} />;
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">AI 빌딩</h2>
        <button type="button" onClick={reset} className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-neutral-200">
          새로 시작
        </button>
      </div>

      {savedTitle ? (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          기록에 저장했어요: <b>{savedTitle}</b>
        </div>
      ) : null}
      {error ? (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      ) : null}

      <AiChat
        messages={messages}
        latestRecommendation={recommendation}
        names={showNames}
        damage={damage}
        loading={loading}
        onSend={handleSend}
        onConfirm={handleConfirm}
        confirming={confirming}
      />
    </div>
  );
}

export default AiCoach;
