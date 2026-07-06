"use client";

import { CalendarDays, RotateCcw, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { getCharacters, getPickupSchedule } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { CharacterCatalogItem, PickupScheduleItem } from "@/lib/types";

const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1);

const categoryStyle = {
  first_pickup: {
    label: "bg-violet-50 text-violet-800 ring-violet-200 dark:bg-violet-400/10 dark:text-violet-200 dark:ring-violet-400/30",
    border: "border-violet-200 bg-violet-50/70 dark:border-violet-400/30 dark:bg-violet-400/10",
    avatar: "border-violet-300 ring-violet-100 dark:border-violet-300 dark:ring-violet-400/20",
    icon: <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  rerun_1: {
    label: "bg-amber-50 text-amber-800 ring-amber-200 dark:bg-amber-400/10 dark:text-amber-200 dark:ring-amber-400/30",
    border: "border-amber-200 bg-amber-50/70 dark:border-amber-400/30 dark:bg-amber-400/10",
    avatar: "border-amber-300 ring-amber-100 dark:border-amber-300 dark:ring-amber-400/20",
    icon: <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />,
  },
  rerun_2: {
    label: "bg-teal-50 text-teal-800 ring-teal-200 dark:bg-teal-400/10 dark:text-teal-200 dark:ring-teal-400/30",
    border: "border-teal-200 bg-teal-50/70 dark:border-teal-400/30 dark:bg-teal-400/10",
    avatar: "border-teal-300 ring-teal-100 dark:border-teal-300 dark:ring-teal-400/20",
    icon: <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />,
  },
} satisfies Record<PickupScheduleItem["category"], { label: string; border: string; avatar: string; icon: ReactNode }>;

export function PickupSchedule() {
  const { t } = useLanguage();
  const [year, setYear] = useState(2026);
  const [items, setItems] = useState<PickupScheduleItem[]>([]);
  const [characters, setCharacters] = useState<CharacterCatalogItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getPickupSchedule(), getCharacters()])
      .then(([schedule, catalog]) => {
        setItems(schedule);
        setCharacters(catalog);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const characterByName = useMemo(() => new Map(characters.map((character) => [character.name, character])), [characters]);
  const years = useMemo(() => {
    const values = new Set(items.map((item) => item.year));
    values.add(2026);
    return Array.from(values).sort((a, b) => b - a);
  }, [items]);

  const yearItems = useMemo(() => items.filter((item) => item.year === year), [items, year]);
  const activeMonths = useMemo(() => new Set(yearItems.map((item) => item.month)), [yearItems]);
  const characterTotal = useMemo(() => yearItems.reduce((sum, item) => sum + item.characters.length, 0), [yearItems]);

  function itemsForMonth(month: number) {
    return yearItems.filter((item) => item.month === month);
  }

  return (
    <section className="grid gap-5">
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel dark:border-slate-800 dark:bg-slate-950">
        <div className="border-b border-slate-200 bg-slate-950 px-4 py-5 text-white dark:border-slate-800 dark:bg-slate-900 sm:px-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="min-w-0">
              <div className="inline-flex items-center gap-2 rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-xs font-medium text-teal-100">
                <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
                {t.pickup.monthly}
              </div>
              <h2 className="mt-3 text-xl font-semibold tracking-normal text-white sm:text-2xl">{t.pickup.title}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">{t.pickup.body}</p>
            </div>
            <label className="grid gap-1 text-sm text-slate-200">
              <span>{t.pickup.year}</span>
              <select className="min-h-10 rounded-md border border-white/15 bg-white px-3 py-2 text-sm font-medium text-slate-950" value={year} onChange={(event) => setYear(Number(event.target.value))}>
                {years.map((item) => (
                  <option key={item} value={item}>
                    {item}년
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="grid gap-3 bg-slate-50 px-4 py-4 dark:bg-slate-900/70 sm:grid-cols-3 sm:px-5">
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t.pickup.yearly}</p>
            <p className="mt-1 text-lg font-semibold text-slate-950 dark:text-slate-50">{year}</p>
          </div>
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t.pickup.monthly}</p>
            <p className="mt-1 text-lg font-semibold text-slate-950 dark:text-slate-50">{activeMonths.size}/12</p>
          </div>
          <div className="rounded-md border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{t.pickup.characters}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs font-medium">
              <span className="rounded-md px-2 py-1 ring-1 ring-inset bg-violet-50 text-violet-800 ring-violet-200">{t.pickup.first}</span>
              <span className="rounded-md px-2 py-1 ring-1 ring-inset bg-amber-50 text-amber-800 ring-amber-200">{t.pickup.rerun}</span>
              <span className="rounded-md px-2 py-1 ring-1 ring-inset bg-teal-50 text-teal-800 ring-teal-200">{characterTotal}</span>
            </div>
          </div>
        </div>
        {error ? <p className="mx-4 mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900 sm:mx-5">{error}</p> : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {MONTHS.map((month) => {
          const monthItems = itemsForMonth(month);
          const isEmpty = monthItems.length === 0;
          return (
            <article key={month} className={`min-h-64 overflow-hidden rounded-md border bg-white shadow-panel transition dark:bg-slate-950 ${isEmpty ? "border-dashed border-slate-300 opacity-80 dark:border-slate-700" : "border-slate-200 dark:border-slate-800"}`}>
              <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
                <div className="flex items-center gap-3">
                  <span className={`inline-flex h-10 w-10 items-center justify-center rounded-md text-sm font-semibold ${isEmpty ? "bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400" : "bg-slate-950 text-white dark:bg-teal-500 dark:text-slate-950"}`}>{String(month).padStart(2, "0")}</span>
                  <div>
                    <h3 className="text-base font-semibold text-slate-950 dark:text-slate-50">{month}월</h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{year}년</p>
                  </div>
                </div>
                <span className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-400">
                  {monthItems.length || "-"}
                </span>
              </div>

              {isEmpty ? (
                <div className="flex min-h-44 items-center justify-center px-4 py-6 text-sm text-slate-400 dark:text-slate-500">{t.pickup.empty}</div>
              ) : (
                <div className="grid gap-3 p-4">
                  {monthItems.map((item) => {
                    const style = categoryStyle[item.category];
                    return (
                      <div key={item.id} className={`rounded-md border p-3 ${style.border}`}>
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <h4 className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${style.label}`}>
                            {style.icon}
                            {item.label_ko}
                          </h4>
                          {item.source_links.length > 0 ? (
                            <a href={item.source_links[0]} target="_blank" rel="noreferrer" className="text-xs font-medium text-slate-500 underline-offset-4 hover:text-slate-900 hover:underline dark:text-slate-400 dark:hover:text-slate-100">
                              {t.pickup.source}
                            </a>
                          ) : null}
                        </div>
                        {item.characters.length === 0 ? (
                          <p className="text-sm text-slate-500">-</p>
                        ) : (
                          <div className="flex flex-wrap gap-2.5">
                            {item.characters.map((name) => {
                              const character = characterByName.get(name);
                              const displayName = (t.characterNames as Record<string, string>)[name] ?? name;
                              return (
                                <div key={`${item.id}-${name}`} className="flex min-w-16 flex-col items-center gap-1.5 text-center">
                                  {character?.image ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={character.image} alt={displayName} title={displayName} className={`h-14 w-14 rounded-md border-2 bg-white object-cover shadow-sm ring-4 ${style.avatar}`} />
                                  ) : (
                                    <span className={`inline-flex h-14 w-14 items-center justify-center rounded-md border-2 bg-white text-xs font-semibold shadow-sm ring-4 ${style.avatar}`} title={displayName}>
                                      {displayName.slice(0, 2)}
                                    </span>
                                  )}
                                  <span className="max-w-20 truncate text-xs font-medium text-slate-700 dark:text-slate-200" title={displayName}>
                                    {displayName}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
