"use client";

import { useEffect, useState } from "react";
import { getUpdates } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { GameUpdateSummary } from "@/lib/types";

export function UpdatesSummary() {
  const { t } = useLanguage();
  const [updates, setUpdates] = useState<GameUpdateSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getUpdates()
      .then(setUpdates)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <section className="grid gap-4">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <h2 className="text-lg font-semibold text-slate-950">{t.updates.title}</h2>
        <p className="mt-2 text-sm text-slate-600">{t.updates.body}</p>
        {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p> : null}
      </div>

      {updates.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{t.updates.empty}</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {updates.map((update) => (
            <article key={update.id} className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <span className="rounded-md bg-slate-950 px-2 py-1 text-sm font-semibold text-white">v{update.version}</span>
                  <h3 className="mt-3 text-lg font-semibold text-slate-950">{update.title_ko}</h3>
                </div>
                {update.release_date_kst ? (
                  <span className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                    {t.updates.releaseDate}: {update.release_date_kst}
                  </span>
                ) : null}
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{update.summary_ko}</p>
              {update.highlights_ko.length > 0 ? (
                <ul className="mt-4 grid gap-2 text-sm text-slate-700">
                  {update.highlights_ko.map((highlight) => (
                    <li key={highlight} className="rounded-md bg-slate-50 px-3 py-2">
                      {highlight}
                    </li>
                  ))}
                </ul>
              ) : null}
              {update.source_links.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {update.source_links.map((source, index) => (
                    <a key={source} href={source} target="_blank" rel="noreferrer" className="text-sm font-medium text-teal-700 hover:text-teal-900">
                      {t.updates.source} {index + 1}
                    </a>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
