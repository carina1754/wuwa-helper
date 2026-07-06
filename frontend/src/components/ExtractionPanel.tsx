import { useLanguage } from "@/lib/i18n";
import type { VisionExtractionResult } from "@/lib/types";

interface ExtractionPanelProps {
  extraction: VisionExtractionResult | null;
}

export function ExtractionPanel({ extraction }: ExtractionPanelProps) {
  const { t } = useLanguage();

  if (!extraction) {
    return <section className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-panel">{t.extraction.empty}</section>;
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-950">{t.extraction.title}</h2>
        <span className="text-sm text-slate-500">
          {t.extraction.screen}: {extraction.screen_type}
        </span>
      </div>
      <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-md border border-slate-200 p-3">
          <span className="block text-slate-500">{t.analyzer.character}</span>
          <strong className="mt-1 block text-slate-900">{extraction.snapshot.character_name || t.history.unknown}</strong>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <span className="block text-slate-500">{t.analyzer.level}</span>
          <strong className="mt-1 block text-slate-900">{extraction.snapshot.character_level ?? "-"}</strong>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <span className="block text-slate-500">{t.analyzer.weapon}</span>
          <strong className="mt-1 block text-slate-900">{extraction.snapshot.weapon?.name || "-"}</strong>
        </div>
        <div className="rounded-md border border-slate-200 p-3">
          <span className="block text-slate-500">{t.echoes.title}</span>
          <strong className="mt-1 block text-slate-900">{extraction.snapshot.echoes.length}</strong>
        </div>
      </div>
      {extraction.warnings.length > 0 && (
        <ul className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {extraction.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
