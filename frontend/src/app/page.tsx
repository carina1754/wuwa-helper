"use client";

import { Clock } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CharacterPlanner } from "@/components/CharacterPlanner";
import { PickupSchedule } from "@/components/PickupSchedule";
import { UpdatesSummary } from "@/components/UpdatesSummary";
import type { AppTab } from "@/lib/constants";

function UpdatingNotice({ label }: { label: string }) {
  return (
    <section className="rounded-md border border-slate-200 bg-white p-8 text-center shadow-panel dark:border-slate-800 dark:bg-slate-950">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-md bg-slate-950 text-white dark:bg-teal-500 dark:text-slate-950">
        <Clock className="h-5 w-5" aria-hidden="true" />
      </div>
      <h2 className="mt-4 text-xl font-semibold text-slate-950 dark:text-slate-50">{label}</h2>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">지금 업데이트 중입니다.</p>
    </section>
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
    case "Teams":
      return <UpdatingNotice label="팀" />;
    case "History":
      return <UpdatingNotice label="기록" />;
  }
}

export default function Home() {
  return <AppShell renderTab={renderTab} />;
}
