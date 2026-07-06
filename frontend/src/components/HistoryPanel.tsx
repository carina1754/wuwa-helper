"use client";

import { useEffect, useState } from "react";
import { getHistory } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { AnalysisSession } from "@/lib/types";

export function HistoryPanel() {
  const { t } = useLanguage();
  const [sessions, setSessions] = useState<AnalysisSession[]>([]);
  const [selected, setSelected] = useState<AnalysisSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getHistory().then(setSessions).catch((err) => setError(err.message));
  }, []);

  return (
    <section className="grid gap-4 lg:grid-cols-[20rem_1fr]">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <h2 className="text-lg font-semibold text-slate-950">{t.history.title}</h2>
        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        <div className="mt-3 grid gap-2">
          {sessions.length === 0 && <p className="text-sm text-slate-500">{t.history.empty}</p>}
          {sessions.map((session) => (
            <button key={session.id} type="button" onClick={() => setSelected(session)} className="rounded-md border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">
              <strong>{session.extraction.snapshot.character_name || t.history.unknown}</strong>
              <span className="block text-slate-500">{new Date(session.created_at).toLocaleString()}</span>
            </button>
          ))}
        </div>
      </div>
      <section className="min-h-96 rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        {selected ? (
          <div className="grid gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">{selected.extraction.snapshot.character_name || t.history.unknown}</h2>
              <p className="mt-1 text-sm text-slate-500">{new Date(selected.created_at).toLocaleString()}</p>
              {selected.image_filename ? <p className="mt-1 text-sm text-slate-500">{selected.image_filename}</p> : null}
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-slate-200 p-3">
                <span className="block text-sm text-slate-500">{t.analyzer.level}</span>
                <strong className="mt-1 block text-slate-900">{selected.extraction.snapshot.character_level ?? "-"}</strong>
              </div>
              <div className="rounded-md border border-slate-200 p-3">
                <span className="block text-sm text-slate-500">{t.analyzer.weapon}</span>
                <strong className="mt-1 block text-slate-900">{selected.extraction.snapshot.weapon?.name || "-"}</strong>
              </div>
              <div className="rounded-md border border-slate-200 p-3">
                <span className="block text-sm text-slate-500">{t.diagnosis.title}</span>
                <strong className="mt-1 block text-slate-900">{selected.diagnoses.length}</strong>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {selected.diagnoses.map((diagnosis, index) => (
                <article key={`${diagnosis.target_type}-${diagnosis.target_name}-${index}`} className="rounded-md border border-slate-200 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-medium text-slate-900">{diagnosis.target_name || diagnosis.target_type}</h3>
                    <span className="rounded-md bg-slate-100 px-2 py-1 text-sm text-slate-700">
                      {diagnosis.grade} · {diagnosis.score}
                    </span>
                  </div>
                  <ul className="mt-3 list-disc pl-5 text-sm text-slate-600">
                    {diagnosis.recommended_actions.map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
            {selected.report ? <p className="whitespace-pre-wrap rounded-md bg-slate-50 p-4 text-sm text-slate-700">{selected.report}</p> : null}
          </div>
        ) : (
          <div className="flex min-h-80 items-center justify-center rounded-md border border-dashed border-slate-300 text-sm text-slate-500">{t.history.select}</div>
        )}
      </section>
    </section>
  );
}
