"use client";

import { RotateCcw, Sparkles, Swords, UserRound } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getPickupBanners } from "@/lib/api";
import { API_BASE_URL } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { PickupBanner } from "@/lib/types";

const rarityRing: Record<number, string> = {
  5: "ring-amber-300 dark:ring-amber-400/50",
  4: "ring-violet-300 dark:ring-violet-400/40",
};

function toggleClass(active: boolean): string {
  return active
    ? "border-teal-400 bg-teal-500 text-white shadow-sm dark:bg-teal-500 dark:text-slate-950"
    : "border-slate-300 bg-white text-slate-600 hover:border-slate-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300";
}

export function PickupSchedule() {
  const { t } = useLanguage();
  const [banners, setBanners] = useState<PickupBanner[]>([]);
  const [error, setError] = useState("");
  const [showCharacters, setShowCharacters] = useState(true);
  const [showWeapons, setShowWeapons] = useState(true);

  useEffect(() => {
    getPickupBanners()
      .then(setBanners)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const versions = useMemo(() => {
    const map = new Map<string, PickupBanner[]>();
    for (const banner of banners) {
      const list = map.get(banner.version) ?? [];
      list.push(banner);
      map.set(banner.version, list);
    }
    return Array.from(map, ([version, list]) => ({ version, banners: list }));
  }, [banners]);

  return (
    <section className="grid gap-5">
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel dark:border-slate-800 dark:bg-slate-950">
        <div className="border-b border-slate-200 bg-slate-950 px-4 py-5 text-white dark:border-slate-800 dark:bg-slate-900 sm:px-5">
          <h2 className="text-xl font-semibold text-white sm:text-2xl">{t.pickup.title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{t.pickup.body}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-400">표시:</span>
            <button
              type="button"
              aria-pressed={showCharacters}
              onClick={() => setShowCharacters((value) => !value)}
              className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${toggleClass(showCharacters)}`}
            >
              <UserRound className="h-4 w-4" aria-hidden="true" />
              캐릭터
            </button>
            <button
              type="button"
              aria-pressed={showWeapons}
              onClick={() => setShowWeapons((value) => !value)}
              className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${toggleClass(showWeapons)}`}
            >
              <Swords className="h-4 w-4" aria-hidden="true" />
              무기
            </button>
          </div>
        </div>
        {error ? (
          <p className="mx-4 my-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 sm:mx-5">{error}</p>
        ) : null}
      </div>

      {versions.length === 0 && !error ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-950">
          {t.pickup.empty}
        </div>
      ) : null}

      {versions.map(({ version, banners: versionBanners }) => (
        <div key={version} className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel dark:border-slate-800 dark:bg-slate-950">
          <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <span className="inline-flex h-9 items-center justify-center rounded-md bg-slate-950 px-2.5 text-sm font-semibold text-white dark:bg-teal-500 dark:text-slate-950">
              {version}
            </span>
            <h3 className="text-base font-semibold text-slate-950 dark:text-slate-50">버전 픽업</h3>
          </div>

          <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {versionBanners.map((banner) => (
              <article
                key={banner.id}
                className={`rounded-md border p-3 ${
                  banner.is_rerun
                    ? "border-amber-200 bg-amber-50/60 dark:border-amber-400/30 dark:bg-amber-400/5"
                    : "border-violet-200 bg-violet-50/60 dark:border-violet-400/30 dark:bg-violet-400/5"
                }`}
              >
                <div className="mb-3 flex items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${
                      banner.is_rerun
                        ? "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-400/10 dark:text-amber-200 dark:ring-amber-400/30"
                        : "bg-violet-50 text-violet-800 ring-violet-200 dark:bg-violet-400/10 dark:text-violet-200 dark:ring-violet-400/30"
                    }`}
                  >
                    {banner.is_rerun ? <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> : <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />}
                    {banner.is_rerun ? "복각" : "신규"}
                  </span>
                  {banner.end_date ? (
                    <span className="text-xs text-slate-500 dark:text-slate-400">~ {banner.end_date}</span>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-3">
                  {showCharacters
                    ? banner.characters.map((character) => (
                        <div key={`c-${character.name_ko}`} className="flex w-16 flex-col items-center gap-1 text-center">
                          {character.avatar ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${character.avatar}`}
                              alt={character.name_ko}
                              title={character.name_ko}
                              className="h-14 w-14 rounded-md border-2 border-white bg-slate-100 object-cover shadow-sm ring-4 ring-slate-200 dark:border-slate-700 dark:ring-slate-700"
                            />
                          ) : (
                            <span className="inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-white bg-slate-100 text-xs font-semibold text-slate-600 shadow-sm ring-4 ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700" title={character.name_ko}>
                              {character.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-slate-700 dark:text-slate-200" title={character.name_ko}>
                            {character.name_ko}
                          </span>
                        </div>
                      ))
                    : null}

                  {showWeapons
                    ? banner.weapons.map((weapon) => (
                        <div key={`w-${weapon.name_ko}`} className="flex w-16 flex-col items-center gap-1 text-center">
                          {weapon.icon ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${weapon.icon}`}
                              alt={weapon.name_ko}
                              title={weapon.name_ko}
                              className={`h-14 w-14 rounded-md border-2 border-white bg-slate-900 object-contain p-0.5 shadow-sm ring-4 dark:border-slate-700 ${rarityRing[weapon.rarity ?? 0] ?? "ring-slate-200 dark:ring-slate-700"}`}
                            />
                          ) : (
                            <span className={`inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-white bg-slate-100 text-[10px] font-semibold text-slate-600 shadow-sm ring-4 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 ${rarityRing[weapon.rarity ?? 0] ?? "ring-slate-200 dark:ring-slate-700"}`} title={weapon.name_ko}>
                              {weapon.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-slate-700 dark:text-slate-200" title={weapon.name_ko}>
                            {weapon.name_ko}
                          </span>
                        </div>
                      ))
                    : null}

                  {!showCharacters && !showWeapons ? (
                    <p className="text-xs text-slate-400">캐릭터 또는 무기를 선택하세요.</p>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
