"use client";

import { CatalogIcon } from "./CatalogIcon";
import { useLanguage } from "@/lib/i18n";
import type { PartyDamage } from "@/lib/partyDamage";
import type { Recommendation } from "@/lib/types";

export interface NameMaps {
  resonator: Map<string, string>;
  weapon: Map<string, string>;
  echo: Map<string, string>;
  sonata: Map<string, string>;
}

/** 확정 전 추천안 카드. 팀별 캐릭터/무기/에코 아이콘 + 근거 + 업그레이드 순서 + 확정 버튼. */
const SHARE_COLOR = ["bg-indigo-500", "bg-sky-500", "bg-emerald-500", "bg-amber-500"];

/** LLM이 업그레이드 순서 문자열에 섞어 넣은 id를 정리한다: "루시(1511)"→"루시", 단독 id→이름. */
function humanizeUpgrade(step: string, names: NameMaps): string {
  const all = new Map<string, string>();
  for (const m of [names.resonator, names.weapon, names.echo, names.sonata]) {
    for (const [k, v] of m) all.set(k, v);
  }
  return step
    .replace(/\((\d{2,})\)/g, "") // 이름 뒤 괄호 id 제거
    .replace(/\b(\d{3,})\b/g, (m, id) => all.get(id) ?? m) // 단독 id는 이름으로(맵에 있을 때만)
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function RecommendationCard({
  recommendation,
  names,
  damage,
  onConfirm,
  confirming = false,
}: {
  recommendation: Recommendation;
  names: NameMaps;
  damage?: PartyDamage | null;
  onConfirm?: () => void;
  confirming?: boolean;
}) {
  const rec = recommendation;
  const { t } = useLanguage();
  return (
    <div className="rounded-lg border border-slate-300 bg-white/60 p-4 shadow-sm dark:border-neutral-700 dark:bg-neutral-900/60">
      {rec.summary ? <h3 className="text-base font-semibold">{rec.summary}</h3> : null}

      {damage ? (
        <div className="mt-3 rounded-md border border-indigo-200 bg-indigo-50/70 p-3 dark:border-indigo-900 dark:bg-indigo-950/40">
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-slate-700 dark:text-neutral-200">{t.recommendation.partyDamageIndex}</span>
            <span className="text-lg font-bold tabular-nums text-indigo-700 dark:text-indigo-300">
              ≈ {damage.total.toLocaleString()}
            </span>
          </div>
          <div className="mt-2 flex h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-neutral-800">
            {damage.rows.map((r, i) =>
              r.share > 0 ? (
                <div key={r.resonatorId} className={SHARE_COLOR[i % SHARE_COLOR.length]} style={{ width: `${r.share * 100}%` }} />
              ) : null,
            )}
          </div>
          <div className="mt-2 grid gap-0.5 text-xs text-slate-600 dark:text-neutral-300">
            {damage.rows.map((r, i) => (
              <div key={r.resonatorId} className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className={`inline-block h-2 w-2 rounded-full ${SHARE_COLOR[i % SHARE_COLOR.length]}`} />
                  {names.resonator.get(r.resonatorId) ?? r.resonatorId}
                </span>
                <span className="tabular-nums text-slate-400">
                  {r.index.toLocaleString()} ({Math.round(r.share * 100)}%)
                </span>
              </div>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-slate-400 dark:text-neutral-500">
            {t.recommendation.damageNote}
          </p>
        </div>
      ) : null}

      <div className="mt-3 grid gap-3">
        {rec.team.map((pick, i) => {
          const resName = names.resonator.get(pick.resonator_id) ?? pick.resonator_id;
          return (
            <div key={`${pick.resonator_id}-${i}`} className="rounded-md border border-slate-200 p-3 dark:border-neutral-800">
              <div className="flex items-center gap-3">
                <CatalogIcon kind="resonator" id={pick.resonator_id} label={resName} size={44} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{resName}</span>
                    {pick.role ? (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[11px] text-slate-700 dark:bg-neutral-800 dark:text-neutral-300">
                        {t.roles[pick.role] ?? pick.role}
                      </span>
                    ) : null}
                  </div>
                  {pick.reason ? <p className="mt-0.5 text-xs text-slate-500 dark:text-neutral-400">{pick.reason}</p> : null}
                </div>
              </div>

              {(pick.weapon || pick.echo) && (
                <div className="mt-3 flex flex-wrap gap-4">
                  {pick.weapon ? (
                    <div>
                      <p className="mb-1 text-[11px] font-medium text-slate-500 dark:text-neutral-400">{t.recommendation.weapon}</p>
                      <div className="flex items-center gap-2">
                        <CatalogIcon kind="weapon" id={pick.weapon.id} label={names.weapon.get(pick.weapon.id)} size={36} />
                        <div className="text-xs">
                          <div>{names.weapon.get(pick.weapon.id) ?? pick.weapon.id}</div>
                          {pick.weapon.alt_ids.length > 0 ? (
                            <div className="text-slate-400">
                              {t.recommendation.altPrefix} {pick.weapon.alt_ids.map((a) => names.weapon.get(a) ?? a).join(", ")}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {pick.echo ? (
                    <div>
                      <p className="mb-1 text-[11px] font-medium text-slate-500 dark:text-neutral-400">{t.recommendation.echoSonata}</p>
                      <div className="flex items-center gap-2">
                        {pick.echo.main_echo_id ? (
                          <CatalogIcon kind="echo" id={pick.echo.main_echo_id} label={names.echo.get(pick.echo.main_echo_id)} size={36} />
                        ) : null}
                        <div className="text-xs">
                          {pick.echo.main_echo_id ? (
                            <div>{t.recommendation.mainPrefix} {names.echo.get(pick.echo.main_echo_id) ?? pick.echo.main_echo_id}</div>
                          ) : null}
                          {pick.echo.sonata_ids.length > 0 ? (
                            <div>{pick.echo.sonata_ids.map((s) => names.sonata.get(s) ?? s).join(" + ")}</div>
                          ) : null}
                          {Object.entries(pick.echo.main_stats).map(([k, v]) => (
                            <div key={k} className="text-slate-400">
                              {k}: {v}
                            </div>
                          ))}
                          {pick.echo.sub_stats && pick.echo.sub_stats.length > 0 ? (
                            <div className="mt-0.5 text-slate-400">{t.recommendation.recommendedSubStats} {pick.echo.sub_stats.join(" · ")}</div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {rec.upgrade_order.length > 0 ? (
        <div className="mt-3">
          <p className="mb-1 text-sm font-medium">{t.recommendation.upgradeOrder}</p>
          <ol className="list-decimal space-y-0.5 pl-5 text-sm text-slate-600 dark:text-neutral-300">
            {rec.upgrade_order.map((step, i) => (
              <li key={i}>{humanizeUpgrade(step, names)}</li>
            ))}
          </ol>
        </div>
      ) : null}

      {onConfirm ? (
        <button
          type="button"
          onClick={onConfirm}
          disabled={confirming}
          className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {confirming ? t.recommendation.saving : t.recommendation.confirm}
        </button>
      ) : null}
    </div>
  );
}

export default RecommendationCard;
