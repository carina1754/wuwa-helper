import { emptyEcho } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { EchoItem, SubStat } from "@/lib/types";

interface EchoEditorProps {
  echoes: EchoItem[];
  onChange: (echoes: EchoItem[]) => void;
}

function normalizeSubStats(subStats: SubStat[]): SubStat[] {
  const next = [...subStats];
  while (next.length < 5) next.push({ name: "", value: "" });
  return next.slice(0, 5);
}

export function EchoEditor({ echoes, onChange }: EchoEditorProps) {
  const { t } = useLanguage();
  const normalized = [...echoes];
  while (normalized.length < 5) normalized.push(emptyEcho(normalized.length + 1));

  function updateEcho(index: number, patch: Partial<EchoItem>) {
    const next = normalized.slice(0, 5).map((echo, echoIndex) => (echoIndex === index ? { ...echo, ...patch } : echo));
    onChange(next);
  }

  return (
    <section className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
      <h2 className="text-lg font-semibold text-slate-950">{t.echoes.title}</h2>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        {normalized.slice(0, 5).map((echo, index) => {
          const subStats = normalizeSubStats(echo.sub_stats);
          return (
            <div key={index} className="rounded-md border border-slate-200 p-3">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-800">
                  {t.echoes.echo} {index + 1}
                </h3>
                <span className="text-xs text-slate-500">
                  {t.echoes.slot} {echo.slot || index + 1}
                </span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <input className="rounded-md border px-3 py-2" placeholder={t.echoes.echoName} value={echo.name ?? ""} onChange={(e) => updateEcho(index, { name: e.target.value })} />
                <input className="rounded-md border px-3 py-2" placeholder={t.echoes.set} value={echo.set_name ?? ""} onChange={(e) => updateEcho(index, { set_name: e.target.value })} />
                <input className="rounded-md border px-3 py-2" placeholder={t.echoes.mainStat} value={echo.main_stat ?? ""} onChange={(e) => updateEcho(index, { main_stat: e.target.value })} />
                <input className="rounded-md border px-3 py-2" placeholder={t.echoes.level} type="number" value={echo.level ?? ""} onChange={(e) => updateEcho(index, { level: e.target.value ? Number(e.target.value) : null })} />
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {subStats.map((stat, statIndex) => (
                  <div key={statIndex} className="grid grid-cols-2 gap-2">
                    <input
                      className="rounded-md border px-2 py-1 text-sm"
                      placeholder={t.echoes.subStat}
                      value={stat.name ?? ""}
                      onChange={(event) => {
                        const nextSubStats = normalizeSubStats(echo.sub_stats);
                        nextSubStats[statIndex] = { ...nextSubStats[statIndex], name: event.target.value };
                        updateEcho(index, { sub_stats: nextSubStats });
                      }}
                    />
                    <input
                      className="rounded-md border px-2 py-1 text-sm"
                      placeholder={t.echoes.value}
                      value={stat.value ?? ""}
                      onChange={(event) => {
                        const nextSubStats = normalizeSubStats(echo.sub_stats);
                        nextSubStats[statIndex] = { ...nextSubStats[statIndex], value: event.target.value };
                        updateEcho(index, { sub_stats: nextSubStats });
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
