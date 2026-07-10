"use client";

import { AiCoach } from "@/components/AiCoach";
import { AiHistory } from "@/components/AiHistory";
import { AppShell } from "@/components/AppShell";
import { Codex } from "@/components/Codex";
import { PickupSchedule } from "@/components/PickupSchedule";
import { SnapshotDamage } from "@/components/SnapshotDamage";
import { TeamBuilder } from "@/components/TeamBuilder";
import { UpdatesSummary } from "@/components/UpdatesSummary";
import { WebsiteUpdates } from "@/components/WebsiteUpdates";
import type { AppTab } from "@/lib/constants";

function renderTab(tab: AppTab) {
  switch (tab) {
    case "Ai":
      return <AiCoach />;
    case "Planner":
      return <Codex />;
    case "PickupSchedule":
      return <PickupSchedule />;
    case "Updates":
      return <UpdatesSummary />;
    case "SiteUpdates":
      return <WebsiteUpdates />;
    case "Teams":
      return <TeamBuilder />;
    case "Snapshot":
      return <SnapshotDamage />;
    case "History":
      return <AiHistory />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
