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
      <div className="rounded-md border border-[var(--line)] bg-[var(--surface)] p-4 shadow-panel">
        <h2 className="text-lg font-semibold text-[var(--fg)]">{t.siteUpdates.title}</h2>
        <p className="mt-2 text-sm text-[var(--fg-soft)]">{t.siteUpdates.body}</p>
        {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p> : null}
      </div>

      {entries.length === 0 ? (
        <div className="rounded-md border border-dashed border-[var(--line-2)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">{t.siteUpdates.empty}</div>
      ) : (
        <div className="grid gap-4">
          {entries.map((entry) => (
            <article key={entry.id} className="overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--surface)] shadow-panel">
              <header className="flex flex-wrap items-center gap-2 border-b border-[var(--line)] bg-[var(--surface-2)] px-4 py-3">
                {entry.version ? <span className="rounded-md bg-[var(--accent)] px-2 py-0.5 text-xs font-bold text-[var(--accent-ink)]">v{entry.version}</span> : null}
                <h3 className="text-base font-semibold text-[var(--fg)]">{entry.title_ko}</h3>
                <time className="ml-auto text-xs text-[var(--muted)]">{entry.date}</time>
              </header>
              {entry.description_ko ? (
                <ul className="grid gap-2.5 px-4 py-4">
                  {entry.description_ko.split("\n").map((raw, i) => {
                    const line = raw.replace(/^\s*[•-]\s*/, "").trim();
                    if (!line) return null;
                    const ci = line.indexOf(":");
                    const label = ci > 0 && ci <= 24 ? line.slice(0, ci) : null;
                    const rest = label ? line.slice(ci + 1).trim() : line;
                    return (
                      <li key={i} className="flex gap-2.5 text-sm leading-6">
                        <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]" aria-hidden />
                        <span className="text-[var(--fg-soft)]">
                          {label ? <span className="font-semibold text-[var(--fg)]">{label}: </span> : null}
                          {rest}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
