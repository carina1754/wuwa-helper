"use client";

import Link from "next/link";
import { useSession } from "next-auth/react";
import { ArrowLeft } from "lucide-react";
import { RulesManager } from "@/components/RulesManager";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useLanguage } from "@/lib/i18n";

export default function AdminPage() {
  const { data: session, status } = useSession();
  const { t } = useLanguage();
  const isAdmin = session?.user?.role === "admin";

  if (status === "loading") {
    return (
      <main className="min-h-screen bg-[#f4f7fb] px-4 py-6 text-slate-900">
        <section className="mx-auto max-w-5xl rounded-md border border-slate-200 bg-white p-4 shadow-panel">{t.app.loading}</section>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="min-h-screen bg-[#f4f7fb] px-4 py-6 text-slate-900">
        <section className="mx-auto max-w-5xl rounded-md border border-slate-200 bg-white p-4 shadow-panel">
          <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-950">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            WuWa AI Coach
          </Link>
          <h1 className="mt-6 text-2xl font-semibold text-slate-950">{t.admin.title}</h1>
          <p className="mt-2 text-sm text-slate-600">{t.admin.restricted}</p>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f4f7fb] px-4 py-6 text-slate-900">
      <div className="mx-auto grid max-w-5xl gap-4">
        <Link href="/" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-950">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          WuWa AI Coach
        </Link>
        <section>
          <h1 className="text-2xl font-semibold text-slate-950">{t.admin.title}</h1>
          <p className="mt-1 text-sm text-slate-600">{t.admin.body}</p>
        </section>
        <RulesManager />
        <SettingsPanel />
      </div>
    </main>
  );
}
