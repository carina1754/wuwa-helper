import { useLanguage } from "@/lib/i18n";

export function Dashboard() {
  const { t } = useLanguage();

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {t.dashboard.cards.map(([title, body]) => (
        <section key={title} className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
          <h2 className="font-semibold text-slate-950">{title}</h2>
          <p className="mt-2 text-sm text-slate-600">{body}</p>
        </section>
      ))}
    </div>
  );
}
