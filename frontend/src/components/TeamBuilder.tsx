import { useLanguage } from "@/lib/i18n";

export function TeamBuilder() {
  const { t } = useLanguage();

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <h2 className="text-lg font-semibold text-slate-950">{t.teams.title}</h2>
      <p className="mt-2 text-sm text-slate-600">{t.teams.body}</p>
    </section>
  );
}
