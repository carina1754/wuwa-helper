"use client";

import { ArrowLeft, LogIn } from "lucide-react";
import { signIn, useSession } from "next-auth/react";
import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/i18n";

export default function LoginPage() {
  const router = useRouter();
  const { status } = useSession();
  const { t } = useLanguage();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/");
    }
  }, [router, status]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f4f7fb] px-4 text-slate-900">
      <section className="w-full max-w-sm rounded-md border border-slate-200 bg-white p-5 shadow-panel">
        <Link href="/" className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-950">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          {t.app.name}
        </Link>
        <h1 className="mt-6 text-2xl font-semibold tracking-normal text-slate-950">{t.login.title}</h1>
        <p className="mt-2 text-sm text-slate-600">{t.login.body}</p>
        <button
          type="button"
          onClick={() => void signIn("google", { callbackUrl: "/" })}
          className="mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          <LogIn className="h-4 w-4" aria-hidden="true" />
          {t.login.google}
        </button>
        <p className="mt-4 text-xs text-slate-500">{t.login.adminEmail}</p>
      </section>
    </main>
  );
}
