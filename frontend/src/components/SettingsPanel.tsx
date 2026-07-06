"use client";

import { Download, Upload } from "lucide-react";
import { useState } from "react";
import { exportData, importData } from "@/lib/api";
import { API_BASE_URL } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";

export function SettingsPanel() {
  const { t } = useLanguage();
  const [message, setMessage] = useState("");

  async function downloadExport() {
    const data = await exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "wuwa-ai-coach-export.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function uploadImport(file: File) {
    const payload = JSON.parse(await file.text());
    const result = await importData(payload);
    setMessage(t.settings.imported(result.rules, result.history, result.characters ?? 0));
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <h2 className="text-lg font-semibold text-slate-950">{t.settings.title}</h2>
      <dl className="mt-4 grid gap-3 text-sm text-slate-700">
        <div>
          <dt className="font-medium">{t.settings.apiBaseUrl}</dt>
          <dd>{API_BASE_URL}</dd>
        </div>
        <div>
          <dt className="font-medium">{t.settings.openAiKey}</dt>
          <dd>{t.settings.openAiKeyBody}</dd>
        </div>
        <div>
          <dt className="font-medium">{t.settings.legalNotice}</dt>
          <dd>{t.settings.legalNoticeBody}</dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={downloadExport} className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white">
          <Download className="h-4 w-4" aria-hidden="true" /> {t.settings.exportJson}
        </button>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
          <Upload className="h-4 w-4" aria-hidden="true" /> {t.settings.importJson}
          <input
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadImport(file).catch((error) => setMessage(error.message));
            }}
          />
        </label>
      </div>
      {message && <p className="mt-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{message}</p>}
    </section>
  );
}
