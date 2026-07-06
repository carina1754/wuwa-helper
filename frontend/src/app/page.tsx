"use client";

import { AppShell } from "@/components/AppShell";
import { CharacterPlanner } from "@/components/CharacterPlanner";
import { Dashboard } from "@/components/Dashboard";
import { HistoryPanel } from "@/components/HistoryPanel";
import { PickupSchedule } from "@/components/PickupSchedule";
import { ScreenshotAnalyzer } from "@/components/ScreenshotAnalyzer";
import { TeamBuilder } from "@/components/TeamBuilder";
import { UpdatesSummary } from "@/components/UpdatesSummary";
import type { AppTab } from "@/lib/constants";

function renderTab(tab: AppTab) {
  switch (tab) {
    case "Dashboard":
      return <Dashboard />;
    case "Analyzer":
      return <ScreenshotAnalyzer />;
    case "Planner":
      return <CharacterPlanner />;
    case "PickupSchedule":
      return <PickupSchedule />;
    case "Updates":
      return <UpdatesSummary />;
    case "Teams":
      return <TeamBuilder />;
    case "History":
      return <HistoryPanel />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
