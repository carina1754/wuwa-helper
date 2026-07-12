"use client";

import { useLanguage } from "@/lib/i18n";
import { Portal } from "./Portal";

// 후원(커피 한 잔) 모달 — 광고 없이 운영하는 사이트의 후원 안내. 국내는 토스페이 QR,
// 해외는 PayPal 링크. 사이트 디자인 언어(모노 킥커 + 골드/틸 토큰 + 얇은 라인 카드)를 따른다.

function CoffeeIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 8h1a3 3 0 0 1 0 6h-1" />
      <path d="M3 8h14v6a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8z" />
      <path d="M7 2v2M11 2v2M15 2v2" />
    </svg>
  );
}

function PaypalIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 20l1.8-11.5A1.5 1.5 0 0 1 10.3 7H14a4 4 0 0 1 0 8h-3.2" />
      <path d="M10 20l1.6-10A1.5 1.5 0 0 1 13.1 8.7H16a3.5 3.5 0 0 1 0 7h-2.6" />
    </svg>
  );
}

export function SupportModal({ onClose }: { onClose: () => void }) {
  const { t } = useLanguage();
  return (
    <Portal>
      <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/60 p-4 backdrop-blur-[2px]" role="dialog" aria-modal="true" aria-label={t.support.title} onClick={onClose}>
        <div className="mt-10 w-full max-w-sm overflow-hidden rounded-2xl border border-[var(--line-2)] bg-[var(--surface)] shadow-2xl" onClick={(e) => e.stopPropagation()}>
          {/* 상단 — 사이트 섹션 헤더 문법(모노 킥커 + 타이틀) */}
          <div className="relative border-b border-[var(--line)] px-5 pb-4 pt-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-[var(--gold)]">support</p>
            <div className="mt-1.5 flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-[11px] border border-[var(--line-2)] bg-[var(--surface-2)] text-[var(--accent)]">
                <CoffeeIcon className="h-[18px] w-[18px]" />
              </span>
              <h2 className="text-lg font-extrabold tracking-tight text-[var(--fg)]">{t.support.title}</h2>
            </div>
            <button type="button" onClick={onClose} aria-label={t.codex.close} className="iconbtn absolute right-4 top-4 !h-8 !w-8 !rounded-lg">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          </div>

          <div className="px-5 py-4">
            <p className="text-sm leading-relaxed text-[var(--fg-soft)]">
              {t.support.bodyIntro}
              <br />
              {t.support.bodyPrefix}<b className="text-[var(--accent)]">{t.support.bodyCoffee}</b>{t.support.bodySuffix}
            </p>

            {/* 토스페이 QR */}
            <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] p-4">
              <div className="mx-auto w-fit rounded-xl bg-white p-2.5 ring-1 ring-[color-mix(in_srgb,var(--accent)_45%,transparent)]">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/donate.jpg" alt={t.support.tossQrAlt} className="h-44 w-44 object-contain" />
              </div>
              <p className="mt-3 text-center text-sm font-semibold text-[var(--fg)]">{t.support.tossScan}</p>
              <p className="mt-0.5 text-center text-xs text-[var(--muted)]">{t.support.tossInstruction}</p>
            </div>

            {/* PayPal — 해외 후원용(토스는 국내 전용) */}
            <a
              href="https://paypal.me/wuwahelper"
              target="_blank"
              rel="noreferrer"
              className="mt-3 flex items-center justify-center gap-2.5 rounded-xl border border-[var(--line)] bg-[var(--surface-2)] px-4 py-3 text-sm font-semibold text-[var(--fg)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              <PaypalIcon className="h-[18px] w-[18px] text-[var(--accent)]" />
              {t.support.paypalDonate}
            </a>
            <p className="mt-1.5 text-center text-xs text-[var(--muted)]">
              {t.support.paypalNote}
            </p>
          </div>

          <div className="border-t border-[var(--line)] bg-[var(--surface-2)] px-5 py-3">
            <p className="text-center text-xs text-[var(--muted)]">{t.support.footerNote}</p>
          </div>
        </div>
      </div>
    </Portal>
  );
}
