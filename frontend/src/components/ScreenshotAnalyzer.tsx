"use client";

import { Play, Save, ScanLine } from "lucide-react";
import { useState } from "react";
import { analyzeCharacter, extractVision, saveHistory } from "@/lib/api";
import { emptySnapshot, ROLES } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { AnalyzeResponse, CharacterSnapshot, VisionExtractionResult } from "@/lib/types";
import { DiagnosisResult } from "./DiagnosisResult";
import { EchoEditor } from "./EchoEditor";
import { ExtractionPanel } from "./ExtractionPanel";
import { ImageUploader } from "./ImageUploader";

export function ScreenshotAnalyzer() {
  const { t } = useLanguage();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<VisionExtractionResult | null>(null);
  const [snapshot, setSnapshot] = useState<CharacterSnapshot>(emptySnapshot());
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  function updateSnapshot(patch: Partial<CharacterSnapshot>) {
    setSnapshot((current) => ({ ...current, ...patch }));
  }

  async function runExtraction() {
    if (!file) {
      setError(t.analyzer.selectImageFirst);
      return;
    }
    setError("");
    setStatus(t.analyzer.extracting);
    try {
      const next = await extractVision(file);
      setExtraction(next);
      setSnapshot(next.snapshot);
      setStatus(t.analyzer.extractionReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.analyzer.extractionFailed);
    }
  }

  async function runDiagnosis() {
    setError("");
    setStatus(t.analyzer.diagnosisRunning);
    try {
      const next = await analyzeCharacter(snapshot, snapshot.role ?? "main_dps");
      setResult(next);
      setStatus(t.analyzer.diagnosisComplete);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.analyzer.diagnosisFailed);
    }
  }

  async function saveCurrentHistory() {
    if (!extraction || !result) {
      setError(t.analyzer.saveRequirement);
      return;
    }
    try {
      await saveHistory({
        id: crypto.randomUUID(),
        created_at: new Date().toISOString(),
        image_filename: file?.name ?? null,
        extraction,
        diagnoses: result.diagnoses,
        report: result.report,
        metadata: { source: "frontend" },
      });
      setStatus(t.analyzer.saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.analyzer.saveFailed);
    }
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(18rem,24rem)_1fr]">
        <ImageUploader
          previewUrl={previewUrl}
          onFileSelected={(nextFile) => {
            setFile(nextFile);
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            setPreviewUrl(URL.createObjectURL(nextFile));
          }}
        />
        <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
          <h2 className="text-lg font-semibold text-slate-950">{t.analyzer.manualEditor}</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.character} value={snapshot.character_name ?? ""} onChange={(e) => updateSnapshot({ character_name: e.target.value })} />
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.level} type="number" value={snapshot.character_level ?? ""} onChange={(e) => updateSnapshot({ character_level: e.target.value ? Number(e.target.value) : null })} />
            <select className="rounded-md border px-3 py-2" value={snapshot.role ?? "main_dps"} onChange={(e) => updateSnapshot({ role: e.target.value as CharacterSnapshot["role"] })}>
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {t.roles[role]}
                </option>
              ))}
            </select>
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.weapon} value={snapshot.weapon?.name ?? ""} onChange={(e) => updateSnapshot({ weapon: { ...(snapshot.weapon ?? {}), name: e.target.value } })} />
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.atk} value={snapshot.stats.atk ?? ""} onChange={(e) => updateSnapshot({ stats: { ...snapshot.stats, atk: e.target.value } })} />
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.critRate} value={snapshot.stats.crit_rate ?? ""} onChange={(e) => updateSnapshot({ stats: { ...snapshot.stats, crit_rate: e.target.value } })} />
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.critDmg} value={snapshot.stats.crit_dmg ?? ""} onChange={(e) => updateSnapshot({ stats: { ...snapshot.stats, crit_dmg: e.target.value } })} />
            <input className="rounded-md border px-3 py-2" placeholder={t.analyzer.energyRegen} value={snapshot.stats.energy_regen ?? ""} onChange={(e) => updateSnapshot({ stats: { ...snapshot.stats, energy_regen: e.target.value } })} />
          </div>
        </section>
      </div>

      <div className="flex flex-wrap gap-2 rounded-md border border-slate-200 bg-white p-3 shadow-panel">
        <button type="button" onClick={runExtraction} className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white">
          <ScanLine className="h-4 w-4" aria-hidden="true" /> {t.analyzer.analyzeImage}
        </button>
        <button type="button" onClick={runDiagnosis} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white">
          <Play className="h-4 w-4" aria-hidden="true" /> {t.analyzer.runDiagnosis}
        </button>
        <button type="button" onClick={saveCurrentHistory} className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700">
          <Save className="h-4 w-4" aria-hidden="true" /> {t.analyzer.saveHistory}
        </button>
      </div>

      {status && <p className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">{status}</p>}
      {error && <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>}

      <EchoEditor echoes={snapshot.echoes} onChange={(echoes) => updateSnapshot({ echoes })} />
      <ExtractionPanel extraction={extraction} />
      <DiagnosisResult result={result} />
    </div>
  );
}
