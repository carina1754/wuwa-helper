import { useLanguage } from "@/lib/i18n";

const PRIORITY_CHIPS = ["壹", "貳", "參"];

export function Dashboard() {
  const { t } = useLanguage();

  return (
    <>
      <div className="bhead">
        <div className="kick">{t.tabs.Dashboard}</div>
        <h1>{t.dashboard.cards[0]?.[0]}</h1>
        <p>{t.dashboard.cards[0]?.[1]}</p>
      </div>
      {t.dashboard.cards.map(([title, body], index) => (
        <div key={title} className="urow" style={{ cursor: "default" }}>
          <span className="ver pchip">{PRIORITY_CHIPS[index] ?? index + 1}</span>
          <span className="um">
            <b>{title}</b>
            <p>{body}</p>
          </span>
        </div>
      ))}
    </>
  );
}
