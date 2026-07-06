"use client";

import { useEffect, useMemo, useState } from "react";
import { getCharacters, getPickupSchedule } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { CharacterCatalogItem, PickupScheduleItem } from "@/lib/types";

const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1);

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

  function itemsForMonth(month: number) {
    return items.filter((item) => item.year === year && item.month === month);
  }

  return (
    <section className="grid gap-4">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">{t.pickup.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{t.pickup.body}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600">
              {t.pickup.year}
              <select className="min-h-10 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900" value={year} onChange={(event) => setYear(Number(event.target.value))}>
                {years.map((item) => (
                  <option key={item} value={item}>
                    {item}년
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
              <span className="text-slate-500">{t.pickup.legend}</span>
              <span className="rounded-md bg-violet-100 px-2 py-1 text-violet-800">{t.pickup.first}</span>
              <span className="rounded-md bg-amber-100 px-2 py-1 text-amber-800">{t.pickup.rerun}</span>
            </div>
          </div>
        </div>
        {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {MONTHS.map((month) => {
          const monthItems = itemsForMonth(month);
          return (
            <article key={month} className="min-h-60 rounded-md border border-slate-200 bg-white p-4 shadow-panel">
              <div className="mb-4 flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-slate-100 text-sm font-semibold text-slate-700">{month}</span>
                <h3 className="text-lg font-semibold text-slate-950">
                  {year}년 {month}월
                </h3>
              </div>
              {monthItems.length === 0 ? (
                <p className="text-sm text-slate-500">-</p>
              ) : (
                <div className="grid gap-4">
                  {monthItems.map((item) => (
                    <div key={item.id}>
                      <h4 className={`mb-2 text-sm font-semibold ${item.category === "first_pickup" ? "text-violet-700" : "text-amber-700"}`}>{item.label_ko}</h4>
                      {item.characters.length === 0 ? (
                        <p className="text-sm text-slate-500">-</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {item.characters.map((name) => {
                            const character = characterByName.get(name);
                            const displayName = (t.characterNames as Record<string, string>)[name] ?? name;
                            return (
                              <div key={`${item.id}-${name}`} className="group relative">
                                {character?.image ? (
                                  // eslint-disable-next-line @next/next/no-img-element
                                  <img src={character.image} alt={displayName} title={displayName} className={`h-11 w-11 rounded-full border-2 object-cover ${item.category === "first_pickup" ? "border-violet-300" : "border-amber-300"}`} />
                                ) : (
                                  <span className={`inline-flex h-11 w-11 items-center justify-center rounded-full border-2 text-xs font-semibold ${item.category === "first_pickup" ? "border-violet-300 bg-violet-50 text-violet-800" : "border-amber-300 bg-amber-50 text-amber-800"}`} title={displayName}>
                                    {name.slice(0, 2)}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
