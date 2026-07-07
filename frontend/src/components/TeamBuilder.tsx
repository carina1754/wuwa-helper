"use client";

import { useEffect, useMemo, useState } from "react";
import { Portal } from "./Portal";
import { getCodexResonators } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { CodexResonator, Role } from "@/lib/types";

const ROLE_ORDER: Role[] = ["main_dps", "sub_dps", "support", "healer"];
const PARTY_SIZE = 3;
const STORAGE_KEY = "mj:party";

function imgSrc(path?: string | null): string | undefined {
  if (!path) return undefined;
  return /^https?:\/\//.test(path) ? path : `/backend${path}`;
}

function rarityRing(rarity: number): string {
  return rarity >= 5 ? "ring-[var(--gold)]" : "ring-[color-mix(in_srgb,var(--accent)_60%,transparent)]";
}

export function TeamBuilder() {
  const { t } = useLanguage();
  const [all, setAll] = useState<CodexResonator[]>([]);
  const [party, setParty] = useState<(number | null)[]>([null, null, null]);
  const [picking, setPicking] = useState<number | null>(null);
  const [element, setElement] = useState("");
  const [role, setRole] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    getCodexResonators()
      .then(setAll)
      .catch(() => {});
  }, []);

  // restore / persist the party across reloads
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
      if (Array.isArray(saved) && saved.length === PARTY_SIZE) setParty(saved);
    } catch {
      /* ignore */
    }
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(party));
    } catch {
      /* ignore */
    }
  }, [party]);

  const byId = useMemo(() => new Map(all.map((r) => [r.id, r])), [all]);
  const selected = party.map((id) => (id != null ? byId.get(id) ?? null : null));

  const elementOptions = useMemo(
    () => [...new Set(all.map((r) => r.element).filter(Boolean))] as string[],
    [all],
  );

  const filtered = useMemo(() => {
    const q = query.trim();
    return all.filter(
      (r) =>
        (!element || r.element === element) &&
        (!role || r.role === role) &&
        (!q || r.name.includes(q) || (r.name_en ?? "").toLowerCase().includes(q.toLowerCase())),
    );
  }, [all, element, role, query]);

  const chosenIds = new Set(party.filter((id): id is number => id != null));

  const roleCounts = useMemo(() => {
    const c = { main_dps: 0, sub_dps: 0, support: 0, healer: 0 } as Record<Role, number>;
    for (const r of selected) if (r) c[r.role] += 1;
    return c;
  }, [selected]);

  const elementCounts = useMemo(() => {
    const c = new Map<string, number>();
    for (const r of selected) if (r?.element) c.set(r.element, (c.get(r.element) ?? 0) + 1);
    return c;
  }, [selected]);

  const notes = useMemo(() => {
    const out: { tone: "good" | "warn"; text: string }[] = [];
    const filled = selected.filter(Boolean).length;
    if (filled === 0) return out;
    if (roleCounts.main_dps === 0) out.push({ tone: "warn", text: "메인 딜러가 없습니다. 주 딜러를 한 명 넣는 것을 권장합니다." });
    if (roleCounts.main_dps > 1) out.push({ tone: "warn", text: "메인 딜러가 2명 이상입니다. 필드 시간이 겹칠 수 있습니다." });
    if (roleCounts.support === 0 && roleCounts.healer === 0)
      out.push({ tone: "warn", text: "서포터/힐러가 없습니다. 생존력·버프가 부족할 수 있습니다." });
    for (const [el, n] of elementCounts)
      if (n >= 2) out.push({ tone: "good", text: `${el} ${n}명 — 동일 속성 시너지(공명 세트)에 유리합니다.` });
    if (filled === PARTY_SIZE && roleCounts.main_dps >= 1 && (roleCounts.support >= 1 || roleCounts.healer >= 1))
      out.push({ tone: "good", text: "딜러 + 서포트 구성이 균형 잡혀 있습니다." });
    return out;
  }, [selected, roleCounts, elementCounts]);

  const closePicker = () => {
    setPicking(null);
    setQuery("");
    setElement("");
    setRole("");
  };

  const pick = (r: CodexResonator) => {
    if (picking == null) return;
    setParty((p) => p.map((id, i) => (i === picking ? r.id : id)));
    closePicker();
  };

  return (
    <section className="grid gap-5">
      <div>
        <h2 className="text-xl font-semibold text-[var(--fg)]">{t.teams.title}</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">공명자 3명으로 파티를 구성하고 역할·속성 시너지를 확인하세요.</p>
      </div>

      {/* party slots */}
      <div className="grid grid-cols-3 gap-3">
        {selected.map((r, i) => (
          <div
            key={i}
            className="relative flex flex-col items-center justify-center rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 text-center"
            style={{ minHeight: 168 }}
          >
            {r ? (
              <>
                <button
                  type="button"
                  onClick={() => setParty((p) => p.map((id, j) => (j === i ? null : id)))}
                  className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
                  aria-label="제거"
                >
                  ✕
                </button>
                {r.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={imgSrc(r.image)}
                    alt={r.name}
                    className={`h-16 w-16 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${rarityRing(r.rarity)}`}
                  />
                ) : (
                  <div className={`grid h-16 w-16 place-items-center rounded-md bg-[var(--surface-2)] text-sm ring-2 ${rarityRing(r.rarity)}`}>
                    {r.name.slice(0, 2)}
                  </div>
                )}
                <div className="mt-2 text-sm font-semibold text-[var(--fg)]">{r.name}</div>
                <div className="mt-0.5 text-xs text-[var(--muted)]">
                  {r.rarity}★ · {r.element} · {t.roles[r.role]}
                </div>
                <button
                  type="button"
                  onClick={() => setPicking(i)}
                  className="mt-2 text-xs text-[var(--accent)] hover:underline"
                >
                  교체
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setPicking(i)}
                className="flex h-full w-full flex-col items-center justify-center gap-2 text-[var(--muted)] hover:text-[var(--fg)]"
              >
                <span className="grid h-12 w-12 place-items-center rounded-full border border-dashed border-[var(--line-2)] text-xl">+</span>
                <span className="text-xs">공명자 추가</span>
              </button>
            )}
          </div>
        ))}
      </div>

      {/* summary */}
      {selected.some(Boolean) ? (
        <div className="grid gap-4 rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 sm:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold text-[var(--fg)]">역할 구성</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {ROLE_ORDER.filter((r) => roleCounts[r] > 0).map((r) => (
                <span key={r} className="rounded-full border border-[var(--line-2)] px-2.5 py-1 text-xs text-[var(--fg-soft)]">
                  {t.roles[r]} ×{roleCounts[r]}
                </span>
              ))}
            </div>
            <h3 className="mt-4 text-sm font-semibold text-[var(--fg)]">속성 구성</h3>
            <div className="mt-2 flex flex-wrap gap-2">
              {[...elementCounts].map(([el, n]) => (
                <span key={el} className="rounded-full border border-[var(--line-2)] px-2.5 py-1 text-xs text-[var(--fg-soft)]">
                  {el} ×{n}
                </span>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-[var(--fg)]">시너지 메모</h3>
            <ul className="mt-2 grid gap-1.5">
              {notes.length === 0 ? (
                <li className="text-xs text-[var(--muted)]">아직 메모가 없습니다.</li>
              ) : (
                notes.map((n, i) => (
                  <li key={i} className="flex gap-2 text-xs">
                    <span className={n.tone === "good" ? "text-[var(--accent)]" : "text-[var(--gold)]"}>
                      {n.tone === "good" ? "✓" : "!"}
                    </span>
                    <span className="text-[var(--fg-soft)]">{n.text}</span>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      ) : null}

      {/* picker modal */}
      {picking != null ? (
        <Portal>
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
            role="dialog"
            aria-modal="true"
            onClick={closePicker}
          >
            <div
              className="relative flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--surface)] shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-2 border-b border-[var(--line)] p-3">
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="공명자 검색"
                  className="min-w-0 flex-1 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--fg)] outline-none"
                />
                <select value={element} onChange={(e) => setElement(e.target.value)} className="rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--fg)]">
                  <option value="">전체 속성</option>
                  {elementOptions.map((el) => (
                    <option key={el} value={el}>{el}</option>
                  ))}
                </select>
                <select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-2 py-1.5 text-sm text-[var(--fg)]">
                  <option value="">전체 역할</option>
                  {ROLE_ORDER.map((r) => (
                    <option key={r} value={r}>{t.roles[r]}</option>
                  ))}
                </select>
                <button type="button" onClick={closePicker} className="grid h-8 w-8 place-items-center rounded-md text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]" aria-label="닫기">
                  ✕
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2 overflow-y-auto p-3 sm:grid-cols-4 md:grid-cols-6">
                {filtered.map((r) => {
                  const taken = chosenIds.has(r.id) && party[picking] !== r.id;
                  return (
                    <button
                      key={r.id}
                      type="button"
                      disabled={taken}
                      onClick={() => pick(r)}
                      title={taken ? "이미 파티에 있습니다" : r.name}
                      className={`flex flex-col items-center gap-1 rounded-md border border-[var(--line)] p-2 text-center transition ${taken ? "cursor-not-allowed opacity-35" : "hover:border-[var(--accent)] hover:bg-[var(--surface-2)]"}`}
                    >
                      {r.image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={imgSrc(r.image)} alt={r.name} className={`h-12 w-12 rounded-md bg-[var(--surface-2)] object-cover ring-2 ${rarityRing(r.rarity)}`} />
                      ) : (
                        <div className={`grid h-12 w-12 place-items-center rounded-md bg-[var(--surface-2)] text-xs ring-2 ${rarityRing(r.rarity)}`}>{r.name.slice(0, 2)}</div>
                      )}
                      <span className="line-clamp-1 text-[11px] text-[var(--fg-soft)]">{r.name}</span>
                    </button>
                  );
                })}
                {filtered.length === 0 ? (
                  <p className="col-span-full py-8 text-center text-sm text-[var(--muted)]">조건에 맞는 공명자가 없습니다.</p>
                ) : null}
              </div>
            </div>
          </div>
        </Portal>
      ) : null}
    </section>
  );
}
