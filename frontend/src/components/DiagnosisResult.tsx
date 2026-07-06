import { useLanguage } from "@/lib/i18n";
import type { AnalyzeResponse } from "@/lib/types";

interface DiagnosisResultProps {
  result: AnalyzeResponse | null;
}

export function DiagnosisResult({ result }: DiagnosisResultProps) {
  const { t } = useLanguage();

  if (!result) {
    return (
      <section className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-panel">
        {t.diagnosis.empty}
      </section>
    );
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <h2 className="text-lg font-semibold text-slate-950">{t.diagnosis.title}</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {result.diagnoses.map((diagnosis, index) => (
          <article key={`${diagnosis.target_type}-${diagnosis.target_name}-${index}`} className="rounded-md border border-slate-200 p-3">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-medium text-slate-900">{diagnosis.target_name || diagnosis.target_type}</h3>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-sm text-slate-700">
                {diagnosis.grade} · {diagnosis.score}
              </span>
            </div>
            <ul className="mt-3 list-disc pl-5 text-sm text-slate-600">
              {diagnosis.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
            <ul className="mt-3 list-disc pl-5 text-sm text-slate-800">
              {diagnosis.recommended_actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
      <pre className="mt-4 whitespace-pre-wrap rounded-md bg-slate-100 p-4 text-sm text-slate-800">{result.report}</pre>
    </section>
  );
}
