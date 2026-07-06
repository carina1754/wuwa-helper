"use client";

import {
  Activity,
  BrainCircuit,
  CalendarDays,
  Globe,
  History,
  Languages,
  LogIn,
  Newspaper,
  Moon,
  Sun,
  Swords,
  Upload,
  UserCircle,
} from "lucide-react";
import { signIn, signOut, useSession } from "next-auth/react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { TABS, type AppTab } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";

const tabIcons: Record<AppTab, ReactNode> = {
  Dashboard: <Activity className="h-4 w-4" aria-hidden="true" />,
  Analyzer: <Upload className="h-4 w-4" aria-hidden="true" />,
  Planner: <BrainCircuit className="h-4 w-4" aria-hidden="true" />,
  PickupSchedule: <CalendarDays className="h-4 w-4" aria-hidden="true" />,
  Updates: <Newspaper className="h-4 w-4" aria-hidden="true" />,
  Teams: <Swords className="h-4 w-4" aria-hidden="true" />,
  History: <History className="h-4 w-4" aria-hidden="true" />,
  SiteUpdates: <Globe className="h-4 w-4" aria-hidden="true" />,
};

interface AppShellProps {
  renderTab: (tab: AppTab) => ReactNode;
}

export function AppShell({ renderTab }: AppShellProps) {
  const [activeTab, setActiveTab] = useState<AppTab>("Updates");
  const [isDark, setIsDark] = useState(false);
  const { data: session, status } = useSession();
  const { language, toggleLanguage, t } = useLanguage();
  const isSignedIn = status === "authenticated";
  const isAdmin = session?.user?.role === "admin";

  return (
    <main className={`min-h-screen transition-colors ${isDark ? "dark bg-slate-950 text-slate-100" : "bg-[#f4f7fb] text-slate-900"}`}>
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur transition-colors dark:border-slate-800 dark:bg-slate-950/95">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="WuWa AI Coach" className="h-8 w-8 rounded-md object-cover" />
                <h1 className="text-2xl font-semibold tracking-normal text-slate-950 dark:text-slate-50">WuWa AI Coach</h1>
              </div>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t.app.tagline}</p>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={toggleLanguage}
                className="inline-flex min-h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
                aria-label={t.app.languageLabel}
                title={t.app.languageLabel}
              >
                <Languages className="h-4 w-4" aria-hidden="true" />
                {language === "ko" ? "KO" : "EN"}
              </button>
              <button
                type="button"
                onClick={() => setIsDark((current) => !current)}
                className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
                aria-label={t.app.themeLabel}
                title={t.app.themeLabel}
              >
                {isDark ? <Sun className="h-4 w-4" aria-hidden="true" /> : <Moon className="h-4 w-4" aria-hidden="true" />}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (isSignedIn) {
                    void signOut({ callbackUrl: "/" });
                    return;
                  }

                  void signIn("google", { callbackUrl: "/" });
                }}
                className="inline-flex min-h-10 items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-teal-500 dark:!text-slate-950 dark:hover:bg-teal-400"
              >
                {isSignedIn ? <UserCircle className="h-4 w-4" aria-hidden="true" /> : <LogIn className="h-4 w-4" aria-hidden="true" />}
                <span className="hidden sm:inline">
                  {isSignedIn ? session.user?.name ?? session.user?.email ?? t.app.signOut : status === "loading" ? t.app.loading : t.app.signIn}
                </span>
              </button>
              {isAdmin ? (
                <Link href="/admin" className="rounded-md border border-teal-300 bg-teal-50 px-3 py-1 text-sm font-medium text-teal-900 transition hover:bg-teal-100 dark:border-teal-400/50 dark:bg-teal-400/10 dark:text-teal-200 dark:hover:bg-teal-400/20">
                  {t.app.admin}
                </Link>
              ) : null}
              <button
                type="button"
                onClick={() => setActiveTab("SiteUpdates")}
                className="rounded-md border border-teal-300 bg-teal-50 px-3 py-1 text-sm font-medium text-teal-900 transition hover:bg-teal-100 dark:border-teal-400/50 dark:bg-teal-400/10 dark:text-teal-200 dark:hover:bg-teal-400/20"
              >
                {t.app.websiteUpdates}
              </button>
            </div>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1" aria-label="Primary">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                  activeTab === tab
                    ? "bg-slate-950 text-white dark:bg-teal-500 dark:!text-slate-950"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {tabIcons[tab]}
                {t.tabs[tab]}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{renderTab(activeTab)}</section>
    </main>
  );
}
