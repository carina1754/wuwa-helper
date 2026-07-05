import type { VisionExtractionResult } from "@/lib/types";

interface ExtractionPanelProps {
  extraction: VisionExtractionResult | null;
}

export function ExtractionPanel({ extraction }: ExtractionPanelProps) {
  if (!extraction) {
    return <section className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-panel">No extraction yet.</section>;
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-950">Extraction</h2>
        <span className="text-sm text-slate-500">Screen: {extraction.screen_type}</span>
      </div>
      {extraction.warnings.length > 0 && (
        <ul className="mb-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {extraction.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      <details className="mb-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">Raw text</summary>
        <pre className="mt-2 whitespace-pre-wrap rounded-md bg-slate-100 p-3 text-xs text-slate-700">{extraction.snapshot.raw_text}</pre>
      </details>
      <details>
        <summary className="cursor-pointer text-sm font-medium text-slate-700">JSON</summary>
        <pre className="mt-2 max-h-96 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-50">
          {JSON.stringify(extraction, null, 2)}
        </pre>
      </details>
    </section>
  );
}
