"use client";

import { useEffect, useState } from "react";
import { getHistory } from "@/lib/api";
import type { AnalysisSession } from "@/lib/types";

export function HistoryPanel() {
  const [sessions, setSessions] = useState<AnalysisSession[]>([]);
  const [selected, setSelected] = useState<AnalysisSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getHistory().then(setSessions).catch((err) => setError(err.message));
  }, []);

  return (
    <section className="grid gap-4 lg:grid-cols-[20rem_1fr]">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <h2 className="text-lg font-semibold text-slate-950">History</h2>
        {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        <div className="mt-3 grid gap-2">
          {sessions.length === 0 && <p className="text-sm text-slate-500">Saved analyses appear here.</p>}
          {sessions.map((session) => (
            <button key={session.id} type="button" onClick={() => setSelected(session)} className="rounded-md border border-slate-200 p-3 text-left text-sm hover:bg-slate-50">
              <strong>{session.extraction.snapshot.character_name || "Unknown"}</strong>
              <span className="block text-slate-500">{new Date(session.created_at).toLocaleString()}</span>
            </button>
          ))}
        </div>
      </div>
      <pre className="min-h-96 overflow-auto rounded-md border border-slate-200 bg-white p-4 text-xs text-slate-700 shadow-panel">
        {selected ? JSON.stringify(selected, null, 2) : "Select a saved session."}
      </pre>
    </section>
  );
}
