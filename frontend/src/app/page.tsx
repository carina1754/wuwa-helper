"use client";

import { AppShell } from "@/components/AppShell";
import { CharacterPlanner } from "@/components/CharacterPlanner";
import { Dashboard } from "@/components/Dashboard";
import { HistoryPanel } from "@/components/HistoryPanel";
import { RulesManager } from "@/components/RulesManager";
import { ScreenshotAnalyzer } from "@/components/ScreenshotAnalyzer";
import { SettingsPanel } from "@/components/SettingsPanel";
import { TeamBuilder } from "@/components/TeamBuilder";
import type { AppTab } from "@/lib/constants";

function renderTab(tab: AppTab) {
  switch (tab) {
    case "Dashboard":
      return <Dashboard />;
    case "Analyzer":
      return <ScreenshotAnalyzer />;
    case "Planner":
      return <CharacterPlanner />;
    case "Teams":
      return <TeamBuilder />;
    case "Rules":
      return <RulesManager />;
    case "History":
      return <HistoryPanel />;
    case "Settings":
      return <SettingsPanel />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
