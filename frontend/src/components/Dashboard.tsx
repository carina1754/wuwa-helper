export function Dashboard() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {[
        ["Recent analysis", "Use History after saving a diagnosis."],
        ["Current priority", "Run Analyzer to identify the weakest echo first."],
        ["Next action", "Fix main stats before optimizing sub-stats."],
      ].map(([title, body]) => (
        <section key={title} className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
          <h2 className="font-semibold text-slate-950">{title}</h2>
          <p className="mt-2 text-sm text-slate-600">{body}</p>
        </section>
      ))}
    </div>
  );
}
