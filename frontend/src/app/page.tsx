"use client";

import { Clock } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CharacterPlanner } from "@/components/CharacterPlanner";
import { PickupSchedule } from "@/components/PickupSchedule";
import { UpdatesSummary } from "@/components/UpdatesSummary";
import { WebsiteUpdates } from "@/components/WebsiteUpdates";
import type { AppTab } from "@/lib/constants";

function UpdatingNotice({ label }: { label: string }) {
  return (
    <div className="soon">
      <span className="sl">
        <Clock aria-hidden="true" />
      </span>
      <h2>{label}</h2>
      <p>지금 준비 중입니다. 먼저 명조 업데이트를 확인해 보세요.</p>
    </div>
  );
}

function renderTab(tab: AppTab) {
  switch (tab) {
    case "Dashboard":
      return <UpdatingNotice label="대시보드" />;
    case "Analyzer":
      return <UpdatingNotice label="분석" />;
    case "Planner":
      return <CharacterPlanner />;
    case "PickupSchedule":
      return <PickupSchedule />;
    case "Updates":
      return <UpdatesSummary />;
    case "SiteUpdates":
      return <WebsiteUpdates />;
    case "Teams":
      return <UpdatingNotice label="팀" />;
    case "History":
      return <UpdatingNotice label="기록" />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
