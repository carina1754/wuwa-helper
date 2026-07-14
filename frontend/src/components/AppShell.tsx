"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";
import { TABS, type AppTab } from "@/lib/constants";
import { LANGUAGES, useLanguage, type Language } from "@/lib/i18n";
import { SupportModal } from "./SupportModal";

function DiscordIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
      <path d="M20.317 4.369a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.058a.082.082 0 0 0 .031.056 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.006.128 12.3 12.3 0 0 1-1.873.891.076.076 0 0 0-.04.107c.36.698.772 1.362 1.225 1.993a.077.077 0 0 0 .084.029 19.84 19.84 0 0 0 6.002-3.03.077.077 0 0 0 .032-.055c.5-5.177-.838-9.674-3.549-13.66a.06.06 0 0 0-.031-.028ZM8.02 15.33c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.332-.956 2.418-2.157 2.418Zm7.975 0c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.332-.946 2.418-2.157 2.418Z" />
    </svg>
  );
}

interface AppShellProps {
  renderTab: (tab: AppTab) => ReactNode;
}

/** Flip and persist the theme exactly like the mockup's themeBtn script. */
function toggleTheme() {
  const root = document.documentElement;
  const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-theme", next);
  try {
    localStorage.setItem("mj:theme", next);
  } catch {
    /* localStorage unavailable — ignore */
  }
}

export function AppShell({ renderTab }: AppShellProps) {
  const [activeTab, setActiveTab] = useState<AppTab>("Updates");
  const [supportOpen, setSupportOpen] = useState(false);
  const { t, language, setLanguage } = useLanguage();

  const selectTab = (tab: AppTab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0 });
  };

  return (
    <>
      <header>
        <div className="wrap">
          <div className="htop">
            <Link className="brand" href="/">
              <span className="seal">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="" aria-hidden="true" />
              </span>
              <b>{t.app.name}</b>
            </Link>
            <div className="hactions">
              <a className="iconbtn" href="https://discord.gg/hPhsf9GN7E" target="_blank" rel="noreferrer" aria-label={t.app.discord} title={t.app.discord}>
                <DiscordIcon />
              </a>
              <button type="button" className="iconbtn tgl" onClick={toggleTheme} aria-label={t.app.themeLabel} title={t.app.themeLabel}>
                <svg className="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
                </svg>
                <svg className="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="4.5" />
                  <path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19" />
                </svg>
              </button>
              <select
                className="langsel"
                value={language}
                onChange={(event) => setLanguage(event.target.value as Language)}
                aria-label={t.app.languageLabel}
                title={t.app.languageLabel}
                style={{
                  background: "transparent",
                  color: "inherit",
                  border: "1px solid currentColor",
                  borderRadius: 999,
                  padding: "3px 8px",
                  fontSize: 12,
                  opacity: 0.8,
                  cursor: "pointer",
                }}
              >
                {LANGUAGES.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
              <Link className="iconbtn" href="/guide" aria-label="이용 가이드" title="이용 가이드">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9.5" />
                  <path d="M9.2 9a2.9 2.9 0 0 1 5.6 1c0 1.8-2.8 2.2-2.8 3.6" />
                  <circle cx="12" cy="17.2" r="0.6" fill="currentColor" stroke="none" />
                </svg>
              </Link>
              <button type="button" className="iconbtn" onClick={() => setSupportOpen(true)} aria-label="커피 한 잔 보태기" title="커피 한 잔 보태기">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M17 8h1a3 3 0 0 1 0 6h-1" />
                  <path d="M3 8h14v6a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8z" />
                  <path d="M7 2v2M11 2v2M15 2v2" />
                </svg>
              </button>
              <button type="button" className="iconbtn" onClick={() => selectTab("SiteUpdates")} aria-label={t.app.websiteUpdates} title={t.app.websiteUpdates}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="m3 11 18-5v12L3 14v-3z" />
                  <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
                </svg>
              </button>
            </div>
          </div>
          <nav className="tabs" aria-label="Primary">
            {TABS.map((tab) => (
              <button key={tab} type="button" className={`tab${activeTab === tab ? " on" : ""}`} onClick={() => selectTab(tab)}>
                {t.tabs[tab]}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main>
        <div className="wrap">
          <section key={activeTab} className="view on">
            {renderTab(activeTab)}
          </section>
        </div>
      </main>

      <footer>
        <p className="disc">Wuthering Waves / Kuro Games와 무관한 비공식 팬 도구입니다.</p>
      </footer>

      {supportOpen ? <SupportModal onClose={() => setSupportOpen(false)} /> : null}
    </>
  );
}
