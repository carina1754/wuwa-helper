"use client";

import { Activity, Archive, BookOpen, BrainCircuit, History, Settings, Swords, Upload } from "lucide-react";
import { useState, type ReactNode } from "react";
import { TABS, type AppTab } from "@/lib/constants";

const tabIcons: Record<AppTab, ReactNode> = {
  Dashboard: <Activity className="h-4 w-4" aria-hidden="true" />,
  Analyzer: <Upload className="h-4 w-4" aria-hidden="true" />,
  Planner: <BrainCircuit className="h-4 w-4" aria-hidden="true" />,
  Teams: <Swords className="h-4 w-4" aria-hidden="true" />,
  Rules: <BookOpen className="h-4 w-4" aria-hidden="true" />,
  History: <History className="h-4 w-4" aria-hidden="true" />,
  Settings: <Settings className="h-4 w-4" aria-hidden="true" />,
};

interface AppShellProps {
  renderTab: (tab: AppTab) => ReactNode;
}

export function AppShell({ renderTab }: AppShellProps) {
  const [activeTab, setActiveTab] = useState<AppTab>("Analyzer");

  return (
    <main className="min-h-screen">
      <header className="border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Archive className="h-6 w-6 text-teal-700" aria-hidden="true" />
                <h1 className="text-2xl font-semibold tracking-normal text-slate-950">WuWa AI Coach</h1>
              </div>
              <p className="mt-1 text-sm text-slate-600">Screenshot extraction, echo scoring, and build priorities</p>
            </div>
            <span className="rounded-md border border-amber-300 bg-amber-50 px-3 py-1 text-sm font-medium text-amber-900">
              비공식 팬 도구
            </span>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1" aria-label="Primary">
            {TABS.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`flex min-h-10 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition ${
                  activeTab === tab ? "bg-slate-950 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {tabIcons[tab]}
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{renderTab(activeTab)}</section>
    </main>
  );
}
