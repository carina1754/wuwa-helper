"use client";

import { useEffect, useState } from "react";
import { getSiteUpdates } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { SiteUpdateEntry } from "@/lib/types";

export function WebsiteUpdates() {
  const { t } = useLanguage();
  const [entries, setEntries] = useState<SiteUpdateEntry[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getSiteUpdates()
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  return (
    <section className="grid gap-4">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <h2 className="text-lg font-semibold text-slate-950">{t.siteUpdates.title}</h2>
        <p className="mt-2 text-sm text-slate-600">{t.siteUpdates.body}</p>
        {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p> : null}
      </div>

      {entries.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{t.siteUpdates.empty}</div>
      ) : (
        <div className="grid gap-4">
          {entries.map((entry) => (
            <article key={entry.id} className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-600">{entry.date}</span>
                {entry.version ? <span className="rounded-md bg-slate-950 px-2 py-1 text-sm font-semibold text-white">v{entry.version}</span> : null}
                <h3 className="text-base font-semibold text-slate-950">{entry.title_ko}</h3>
              </div>
              {entry.description_ko ? <p className="mt-3 text-sm leading-6 text-slate-700">{entry.description_ko}</p> : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
