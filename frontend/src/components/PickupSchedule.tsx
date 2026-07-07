"use client";

import { CalendarDays, Handshake, RotateCcw, Sparkles, Swords, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Portal } from "./Portal";
import { ResonatorDetail, WeaponDetail } from "./Codex";
import { getCodexResonators, getCodexWeapons, getPickupBanners } from "@/lib/api";
import { API_BASE_URL } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { CodexResonator, CodexWeapon, PickupBanner, PickupBannerCharacter, PickupBannerWeapon } from "@/lib/types";

type DetailTarget =
  | { type: "character"; nameKo: string; reso: CodexResonator | null; avatar?: string | null }
  | { type: "weapon"; weapon: PickupBannerWeapon };

type BannerGroup = {
  key: string;
  isRerun: boolean;
  isCollab: boolean;
  startDate?: string | null;
  endDate?: string | null;
  minPhase: number;
  characters: PickupBannerCharacter[];
  weapons: PickupBannerWeapon[];
};

/** Merge a version's banners that share the same run period and category
 * (rerun/collab) into one card — e.g. two reruns running concurrently, or the
 * collab pair — combining their featured characters and weapons. */
function groupBanners(list: PickupBanner[]): BannerGroup[] {
  const groups = new Map<string, BannerGroup>();
  for (const banner of list) {
    const key = `${banner.is_collab ? "c" : "r"}|${banner.is_rerun ? "1" : "0"}|${banner.start_date ?? ""}|${banner.end_date ?? ""}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        isRerun: banner.is_rerun,
        isCollab: banner.is_collab,
        startDate: banner.start_date,
        endDate: banner.end_date,
        minPhase: banner.phase ?? 0,
        characters: [],
        weapons: [],
      };
      groups.set(key, group);
    }
    group.characters.push(...banner.characters);
    group.weapons.push(...banner.weapons);
    group.minPhase = Math.min(group.minPhase, banner.phase ?? 0);
  }
  // regular groups before collab, then chronological by earliest phase
  return [...groups.values()].sort(
    (a, b) => Number(a.isCollab) - Number(b.isCollab) || a.minPhase - b.minPhase,
  );
}

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
    ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-ink)] shadow-sm"
    : "border-[var(--line)] bg-[var(--surface)] text-[var(--fg-soft)] hover:border-[var(--line-2)]";
}

/** 픽업 배너 캐릭터명과 wuwa_resonator 이름을 매칭하기 위한 정규화 (공백·가운뎃점 제거). */
function normalizeName(name: string): string {
  return name.replace(/[\s·・]/g, "");
}

export function PickupSchedule() {
  const { t } = useLanguage();
  const [banners, setBanners] = useState<PickupBanner[]>([]);
  const [resonators, setResonators] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [error, setError] = useState("");
  const [showCharacters, setShowCharacters] = useState(true);
  const [showWeapons, setShowWeapons] = useState(true);
  const [showCollab, setShowCollab] = useState(true);
  const [detail, setDetail] = useState<DetailTarget | null>(null);

  useEffect(() => {
    getPickupBanners()
      .then(setBanners)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    getCodexResonators()
      .then(setResonators)
      .catch(() => {});
    getCodexWeapons()
      .then(setWeapons)
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

  const resonatorByName = useMemo(() => {
    const map = new Map<string, CodexResonator>();
    for (const r of resonators) map.set(normalizeName(r.name), r);
    return map;
  }, [resonators]);

  /** 배너 캐릭터명을 resonator에 매칭. 정규화 직접 매칭 우선, 실패 시
   * '양양·현령'처럼 칭호가 붙은 이름은 가운뎃점 앞 기본명으로 재시도. */
  const matchResonator = (nameKo: string): CodexResonator | null => {
    const direct = resonatorByName.get(normalizeName(nameKo));
    if (direct) return direct;
    const base = nameKo.split(/[·・]/)[0];
    if (base && base !== nameKo) return resonatorByName.get(normalizeName(base)) ?? null;
    return null;
  };

  const weaponByName = useMemo(() => {
    const map = new Map<string, CodexWeapon>();
    for (const w of weapons) map.set(normalizeName(w.name_ko), w);
    return map;
  }, [weapons]);
  const matchWeapon = (nameKo: string): CodexWeapon | null =>
    weaponByName.get(normalizeName(nameKo)) ?? null;

  const tElement = (value?: string | null) => (value ? (t.elements as Record<string, string>)[value] ?? value : "-");
  const tWeaponType = (value?: string | null) => (value ? (t.weaponTypes as Record<string, string>)[value] ?? value : "-");

  const hasCollab = useMemo(() => banners.some((banner) => banner.is_collab), [banners]);

  const versions = useMemo(() => {
    const map = new Map<string, PickupBanner[]>();
    for (const banner of banners) {
      if (!showCollab && banner.is_collab) continue;
      const list = map.get(banner.version) ?? [];
      list.push(banner);
      map.set(banner.version, list);
    }
    return Array.from(map, ([version, list]) => ({ version, groups: groupBanners(list) }));
  }, [banners, showCollab]);

  return (
    <section className="grid gap-5">
      <div className="overflow-hidden rounded-md border border-[var(--line)] bg-[var(--surface)] shadow-panel">
        <div className="border-b border-[var(--line)] bg-[var(--surface-2)] px-4 py-5 text-[var(--fg)] sm:px-5">
          <h2 className="text-xl font-semibold text-[var(--fg)] sm:text-2xl">{t.pickup.title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--fg-soft)]">{t.pickup.body}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-[var(--muted)]">표시:</span>
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
        <div className="rounded-md border border-dashed border-[var(--line)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">
          {t.pickup.empty}
        </div>
      ) : null}

      {versions.map(({ version, groups }) => (
        <div key={version} className="overflow-hidden rounded-md border border-[var(--line)] bg-[var(--surface)] shadow-panel">
          <div className="flex items-center gap-3 border-b border-[var(--line)] bg-[var(--surface-2)] px-4 py-3">
            <span className="inline-flex h-9 items-center justify-center rounded-md bg-[var(--accent)] px-2.5 text-sm font-semibold text-[var(--accent-ink)]">
              {version}
            </span>
            <h3 className="text-base font-semibold text-[var(--fg)]">버전 픽업</h3>
          </div>

          <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {groups.map((group) => (
              <article
                key={`${version}-${group.key}`}
                className={`rounded-md border p-3 ${
                  group.isRerun
                    ? "border-amber-200 bg-amber-50/60 dark:border-amber-400/30 dark:bg-amber-400/5"
                    : "border-violet-200 bg-violet-50/60 dark:border-violet-400/30 dark:bg-violet-400/5"
                }`}
              >
                <div className="mb-2 flex flex-wrap items-center gap-1.5">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${
                      group.isRerun
                        ? "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-400/10 dark:text-amber-200 dark:ring-amber-400/30"
                        : "bg-violet-50 text-violet-800 ring-violet-200 dark:bg-violet-400/10 dark:text-violet-200 dark:ring-violet-400/30"
                    }`}
                  >
                    {group.isRerun ? <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> : <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />}
                    {group.isRerun ? "복각" : "신규"}
                  </span>
                  {group.isCollab ? (
                    <span className="inline-flex items-center gap-1 rounded-md bg-fuchsia-50 px-2 py-1 text-xs font-semibold text-fuchsia-800 ring-1 ring-inset ring-fuchsia-200 dark:bg-fuchsia-400/10 dark:text-fuchsia-200 dark:ring-fuchsia-400/30">
                      <Handshake className="h-3.5 w-3.5" aria-hidden="true" />
                      콜라보
                    </span>
                  ) : null}
                </div>
                {formatPeriod(group.startDate, group.endDate) ? (
                  <p className="mb-3 flex items-start gap-1 text-xs text-[var(--muted)]">
                    <CalendarDays className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{formatPeriod(group.startDate, group.endDate)}</span>
                  </p>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  {showCharacters
                    ? group.characters.map((character, ci) => (
                        <button
                          type="button"
                          key={`c-${character.name_ko}-${ci}`}
                          onClick={() =>
                            setDetail({
                              type: "character",
                              nameKo: character.name_ko,
                              reso: matchResonator(character.name_ko),
                              avatar: character.avatar,
                            })
                          }
                          title={`${character.name_ko} 상세 보기`}
                          className="flex w-16 flex-col items-center gap-1 rounded-md text-center transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          {character.avatar ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${character.avatar}`}
                              alt={character.name_ko}
                              className="h-14 w-14 rounded-md border-2 border-[var(--surface)] bg-[var(--surface-2)] object-cover shadow-sm ring-4 ring-[var(--line)]"
                            />
                          ) : (
                            <span className="inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-[var(--surface)] bg-[var(--surface-2)] text-xs font-semibold text-[var(--fg-soft)] shadow-sm ring-4 ring-[var(--line)]">
                              {character.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-[var(--fg-soft)]">
                            {character.name_ko}
                          </span>
                        </button>
                      ))
                    : null}

                  {showWeapons
                    ? group.weapons.map((weapon, wi) => (
                        <button
                          type="button"
                          key={`w-${weapon.name_ko}-${wi}`}
                          onClick={() => setDetail({ type: "weapon", weapon })}
                          title={`${weapon.name_ko} 상세 보기`}
                          className="flex w-16 flex-col items-center gap-1 rounded-md text-center transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                        >
                          {weapon.icon ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`${API_BASE_URL}${weapon.icon}`}
                              alt={weapon.name_ko}
                              className={`h-14 w-14 rounded-md border-2 border-[var(--surface)] bg-slate-900 object-contain p-0.5 shadow-sm ring-4 ${rarityRing[weapon.rarity ?? 0] ?? "ring-[var(--line)]"}`}
                            />
                          ) : (
                            <span className={`inline-flex h-14 w-14 items-center justify-center rounded-md border-2 border-[var(--surface)] bg-[var(--surface-2)] text-[10px] font-semibold text-[var(--fg-soft)] shadow-sm ring-4 ${rarityRing[weapon.rarity ?? 0] ?? "ring-[var(--line)]"}`}>
                              {weapon.name_ko.slice(0, 2)}
                            </span>
                          )}
                          <span className="w-full truncate text-xs font-medium text-[var(--fg-soft)]">
                            {weapon.name_ko}
                          </span>
                        </button>
                      ))
                    : null}

                  {!showCharacters && !showWeapons ? (
                    <p className="text-xs text-[var(--muted)]">캐릭터 또는 무기를 선택하세요.</p>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>
      ))}

      {detail ? (
        <Portal>
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setDetail(null)}
          >
          <div
            className="relative max-h-[85vh] w-full max-w-md overflow-y-auto rounded-lg border border-[var(--line)] bg-[var(--surface)] p-5 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setDetail(null)}
              aria-label="닫기"
              className="absolute right-3 top-3 rounded-md p-1 text-[var(--muted)] transition hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>

            {detail.type === "character" ? (
              detail.reso ? (
                <ResonatorDetail item={detail.reso} tElement={tElement} />
              ) : (
                <div className="grid justify-items-center gap-3 text-center">
                  {detail.avatar ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={`${API_BASE_URL}${detail.avatar}`}
                      alt=""
                      className="h-24 w-24 rounded-md bg-[var(--surface-2)] object-cover"
                    />
                  ) : null}
                  <div>
                    <h3 className="text-lg font-semibold text-[var(--fg)]">{detail.nameKo}</h3>
                    <p className="mt-1 text-sm text-[var(--muted)]">상세 정보가 아직 없습니다.</p>
                  </div>
                </div>
              )
            ) : matchWeapon(detail.weapon.name_ko) ? (
              <WeaponDetail item={matchWeapon(detail.weapon.name_ko) as CodexWeapon} />
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
                  <h3 className="text-lg font-semibold text-[var(--fg)]">{detail.weapon.name_ko}</h3>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {detail.weapon.rarity ? `${detail.weapon.rarity}★` : ""}
                    {detail.weapon.weapon_type ? `${detail.weapon.rarity ? " · " : ""}${tWeaponType(detail.weapon.weapon_type)}` : ""}
                  </p>
                </div>
              </div>
            )}
          </div>
          </div>
        </Portal>
      ) : null}
    </section>
  );
}
