"use client";

import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { getRules, saveRules } from "@/lib/api";
import type { BuildRule } from "@/lib/types";

export function RulesManager() {
  const [text, setText] = useState("[]");
  const [message, setMessage] = useState("");

  useEffect(() => {
    getRules()
      .then((rules) => setText(JSON.stringify(rules, null, 2)))
      .catch((error) => setMessage(error.message));
  }, []);

  async function save() {
    try {
      const parsed = JSON.parse(text) as BuildRule[];
      const rules = await saveRules(parsed);
      setText(JSON.stringify(rules, null, 2));
      setMessage("Rules saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Rules save failed.");
    }
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-950">Rules Manager</h2>
        <button type="button" onClick={save} className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white">
          <Save className="h-4 w-4" aria-hidden="true" /> Save Rules
        </button>
      </div>
      {message && <p className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{message}</p>}
      <textarea className="mt-4 min-h-[28rem] w-full rounded-md border border-slate-300 p-3 font-mono text-sm" value={text} onChange={(event) => setText(event.target.value)} />
    </section>
  );
}
