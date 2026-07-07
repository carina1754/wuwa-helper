"use client";

import { CalendarDays, Handshake, RotateCcw, Sparkles, Swords, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getCharacters, getPickupBanners } from "@/lib/api";
import { API_BASE_URL, mediaUrl } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { CharacterCatalogItem, PickupBanner, PickupBannerWeapon } from "@/lib/types";

type DetailTarget =
  | { type: "character"; nameKo: string; entry?: CharacterCatalogItem }
  | { type: "weapon"; weapon: PickupBannerWeapon };

/** Phase-1 banners start when the version launches; Namuwiki records that as a
 * relative phrase ("3.5 버전 업데이트 이후") rather than a date. Show a short label
 * for those and the raw date otherwise. */
function formatPeriod(start?: string | null, end?: string | null): string | null {
  const startLabel = start ? (/버전 업데이트 이후/.test(start) ? "버전 출시" : start) : null;
  if (!startLabel && !end) return null;
  if (startLabel && end) return `${startLabel} ~ ${end}`;
  return startLabel ? `${startLabel} ~` : `~ ${end}`;
}

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
  const [characters, setCharacters] = useState<CharacterCatalogItem[]>([]);
  const [error, setError] = useState("");
  const [showCharacters, setShowCharacters] = useState(true);
  const [showWeapons, setShowWeapons] = useState(true);
  const [showCollab, setShowCollab] = useState(true);
  const [detail, setDetail] = useState<DetailTarget | null>(null);

  useEffect(() => {
    getPickupBanners()
      .then(setBanners)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    getCharacters()
      .then(setCharacters)
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!detail) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDetail(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detail]);

  const charById = useMemo(() => {
    const map = new Map<number, CharacterCatalogItem>();
    for (const character of characters) map.set(character.id, character);
    return map;
  }, [characters]);

  const tElement = (value?: string | null) => (value ? (t.elements as Record<string, string>)[value] ?? value : "-");
  const tWeaponType = (value?: string | null) => (value ? (t.weaponTypes as Record<string, string>)[value] ?? value : "-");
  const tSonata = (value: string) => (t.sonataSets as Record<string, string>)[value] ?? value;
  const tWeaponName = (value: string) => (t.weaponNames as Record<string, string>)[value] ?? value;
  const tStat = (value: string) => (t.statNames as Record<string, string>)[value] ?? value;

  const hasCollab = useMemo(() => banners.some((banner) => banner.is_collab), [banners]);

  const versions = useMemo(() => {
    const map = new Map<string, PickupBanner[]>();
    for (const banner of banners) {
      if (!showCollab && banner.is_collab) continue;
      const list = map.get(banner.version) ?? [];
      list.push(banner);
      map.set(banner.version, list);
    }
    // Keep a version's regular banners first, then its collab banners, so the
    // two tracks never interleave within a version block.
    for (const list of map.values()) {
      list.sort((a, b) => Number(a.is_collab) - Number(b.is_collab) || (a.phase ?? 0) - (b.phase ?? 0));
    }
    return Array.from(map, ([version, list]) => ({ version, banners: list }));
  }, [banners, showCollab]);

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
            {hasCollab ? (
              <button
                type="button"
                aria-pressed={showCollab}
                onClick={() => setShowCollab((value) => !value)}
                className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${toggleClass(showCollab)}`}
              >
                <Handshake className="h-4 w-4" aria-hidden="true" />
                콜라보
              </button>
            ) : null}
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
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
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
                  {banner.is_collab ? (
                    <span className="inline-flex items-center gap-1 rounded-md bg-fuchsia-50 px-2 py-1 text-xs font-semibold text-fuchsia-800 ring-1 ring-inset ring-fuchsia-200 dark:bg-fuchsia-400/10 dark:text-fuchsia-200 dark:ring-fuchsia-400/30">
                      <Handshake className="h-3.5 w-3.5" aria-hidden="true" />
                      콜라보
                    </span>
                  ) : null}
                </div>
                {formatPeriod(banner.start_date, banner.end_date) ? (
                  <p className="mb-3 flex items-start gap-1 text-xs text-slate-500 dark:text-slate-400">
                    <CalendarDays className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{formatPeriod(banner.start_date, banner.end_date)}</span>
                  </p>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  {showCharacters
                    ? banner.characters.map((character) => (
                        <button
                          type="button"
                          key={`c-${character.name_ko}`}
                          onClick={() =>
                            setDetail({
                              type: "character",
                              nameKo: character.name_ko,
                              entry: character.catalog_id != null ? charById.get(character.catalog_id) : undefined,
                            })
                          }
                          title={`${character.name_ko} 상세 보기`}
                          className="flex w-16 flex-col items-center gap-1 rounded-md text-center transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
                        >
                          {character.avatar ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${character.avatar}`}
                              alt={character.name_ko}
                              className="h-14 w-14 rounded-md border-2 border-white bg-slate-100 object-cover shadow-sm ring-4 ring-slate-200 dark:border-slate-700 dark:ring-slate-700"
                            />
                          ) : (
                            <span className="inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-white bg-slate-100 text-xs font-semibold text-slate-600 shadow-sm ring-4 ring-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700">
                              {character.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-slate-700 dark:text-slate-200">
                            {character.name_ko}
                          </span>
                        </button>
                      ))
                    : null}

                  {showWeapons
                    ? banner.weapons.map((weapon) => (
                        <button
                          type="button"
                          key={`w-${weapon.name_ko}`}
                          onClick={() => setDetail({ type: "weapon", weapon })}
                          title={`${weapon.name_ko} 상세 보기`}
                          className="flex w-16 flex-col items-center gap-1 rounded-md text-center transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
                        >
                          {weapon.icon ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${weapon.icon}`}
                              alt={weapon.name_ko}
                              className={`h-14 w-14 rounded-md border-2 border-white bg-slate-900 object-contain p-0.5 shadow-sm ring-4 dark:border-slate-700 ${rarityRing[weapon.rarity ?? 0] ?? "ring-slate-200 dark:ring-slate-700"}`}
                            />
                          ) : (
                            <span className={`inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-white bg-slate-100 text-[10px] font-semibold text-slate-600 shadow-sm ring-4 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 ${rarityRing[weapon.rarity ?? 0] ?? "ring-slate-200 dark:ring-slate-700"}`}>
                              {weapon.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-slate-700 dark:text-slate-200">
                            {weapon.name_ko}
                          </span>
                        </button>
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

      {detail ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setDetail(null)}
        >
          <div
            className="relative max-h-[85vh] w-full max-w-sm overflow-y-auto rounded-lg border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setDetail(null)}
              aria-label="닫기"
              className="absolute right-3 top-3 rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>

            {detail.type === "character" ? (
              <div className="grid gap-3">
                {detail.entry?.splash_image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={mediaUrl(detail.entry.splash_image)}
                    alt=""
                    className="w-full rounded-md bg-slate-50 object-contain dark:bg-slate-800"
                    style={{ aspectRatio: "696 / 960" }}
                  />
                ) : detail.entry?.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={mediaUrl(detail.entry.image)} alt="" className="h-24 w-24 self-center rounded-md object-cover" />
                ) : null}
                <div>
                  <h3 className="text-lg font-semibold text-slate-950 dark:text-white">{detail.nameKo}</h3>
                  {detail.entry ? (
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                      {detail.entry.rarity ? `${detail.entry.rarity}★ · ` : ""}
                      {tElement(detail.entry.element)} · {tWeaponType(detail.entry.weapon_type)} · {t.roles[detail.entry.role]}
                    </p>
                  ) : (
                    <p className="mt-1 text-sm text-slate-400">상세 정보가 아직 없습니다.</p>
                  )}
                </div>
                {detail.entry ? (
                  <dl className="grid gap-2 text-sm">
                    <div>
                      <dt className="font-medium text-slate-950 dark:text-slate-200">{t.planner.recommendedSet}</dt>
                      <dd className="text-slate-600 dark:text-slate-300">
                        {detail.entry.default_sonata ? tSonata(detail.entry.default_sonata) : "-"}
                      </dd>
                    </div>
                    {detail.entry.sonata_fallbacks.length > 0 ? (
                      <div>
                        <dt className="font-medium text-slate-950 dark:text-slate-200">{t.planner.fallbackSets}</dt>
                        <dd className="text-slate-600 dark:text-slate-300">{detail.entry.sonata_fallbacks.map(tSonata).join(", ")}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt className="font-medium text-slate-950 dark:text-slate-200">{t.planner.weapon}</dt>
                      <dd className="text-slate-600 dark:text-slate-300">
                        {detail.entry.default_weapon ? tWeaponName(detail.entry.default_weapon) : "-"}
                      </dd>
                    </div>
                    <div>
                      <dt className="font-medium text-slate-950 dark:text-slate-200">{t.planner.bonusStats}</dt>
                      <dd className="text-slate-600 dark:text-slate-300">
                        {detail.entry.bonus_stats.length ? detail.entry.bonus_stats.map(tStat).join(", ") : "-"}
                      </dd>
                    </div>
                  </dl>
                ) : null}
              </div>
            ) : (
              <div className="grid justify-items-center gap-3 text-center">
                {detail.weapon.icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${API_BASE_URL}${detail.weapon.icon}`}
                    alt=""
                    className="h-28 w-28 rounded-md bg-slate-900 object-contain p-1.5"
                  />
                ) : null}
                <div>
                  <h3 className="text-lg font-semibold text-slate-950 dark:text-white">{detail.weapon.name_ko}</h3>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    {detail.weapon.rarity ? `${detail.weapon.rarity}★` : ""}
                    {detail.weapon.weapon_type ? `${detail.weapon.rarity ? " · " : ""}${tWeaponType(detail.weapon.weapon_type)}` : ""}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
