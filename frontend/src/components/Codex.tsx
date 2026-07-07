"use client";

import { ChevronDown, Sparkles, Swords, UserRound, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Portal } from "./Portal";
import { getCodexEchoes, getCodexResonators, getCodexWeapons, getSonataSets } from "@/lib/api";
import { API_BASE_URL } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { CodexEcho, CodexResonator, CodexWeapon, Role, SonataSet } from "@/lib/types";

type SubTab = "resonators" | "weapons" | "echoes";

type Detail =
  | { type: "resonator"; item: CodexResonator }
  | { type: "weapon"; item: CodexWeapon }
  | { type: "echo"; item: CodexEcho };

const ROLE_LABELS: Record<Role, string> = {
  main_dps: "메인 딜러",
  sub_dps: "서브 딜러",
  support: "서포터",
  healer: "힐러",
};

/** Game strings carry UE rich-text markup (<size>, <color>, <te href=…>) and
 * {0}/{1} runtime placeholders. Strip every tag and collapse whitespace so the
 * copy renders as clean prose. Placeholders are left in place. */
function stripTags(input?: string | null): string {
  if (!input) return "";
  return input
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** 5★ gets a warm gold ring, 4★ a violet ring; anything else a neutral line. */
function rarityRing(rarity?: number | null): string {
  if (rarity === 5) return "ring-[var(--gold)]";
  if (rarity === 4) return "ring-violet-400/60";
  return "ring-[var(--line-2)]";
}

/** The image URL is served from the API host; both resonator `image` and
 * weapon/echo `icon` are stored as "/catalog/image/..." paths. */
function imageSrc(path?: string | null): string | undefined {
  if (!path) return undefined;
  // encore.moe images are absolute URLs; local cached assets are /catalog/... paths.
  return /^https?:\/\//.test(path) ? path : `${API_BASE_URL}${path}`;
}

function subTabClass(active: boolean): string {
  return active
    ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-ink)] shadow-sm"
    : "border-[var(--line)] bg-[var(--surface)] text-[var(--fg-soft)] hover:border-[var(--line-2)]";
}

const GRID_CLASS = "grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8";

/** Weapon `resonance` may arrive as an object ({Name}) or (per the raw
 * normalizer default) an array — pull the first non-empty Name either way. */
function weaponResonanceName(weapon: CodexWeapon): string {
  const { resonance } = weapon;
  if (!resonance) return "";
  if (Array.isArray(resonance)) {
    for (const entry of resonance) {
      if (entry?.Name) return entry.Name;
    }
    return "";
  }
  return resonance.Name ?? "";
}

const STAT_KEYS = ["Atk", "Life", "Def", "Crit", "CritDamage"] as const;
const STAT_LABELS: Record<(typeof STAT_KEYS)[number], string> = {
  Atk: "공격력",
  Life: "생명력",
  Def: "방어력",
  Crit: "치명타 확률",
  CritDamage: "치명타 피해",
};

interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  render?: (value: string) => string;
}

function FilterSelect({ label, value, onChange, options, render }: FilterSelectProps) {
  return (
    <select
      aria-label={label}
      className="min-h-9 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--fg)]"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">{label}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {render ? render(option) : option}
        </option>
      ))}
    </select>
  );
}

/** Custom dropdown for the sonata filter that shows each set's crest icon
 * (a native <select> can't render images in its options). */
function SonataFilter({
  value,
  onChange,
  options,
  iconOf,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  iconOf: (name: string) => string | undefined;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  const selectedIcon = value ? imageSrc(iconOf(value)) : undefined;
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="소나타 필터"
        onClick={() => setOpen((current) => !current)}
        className="flex min-h-9 items-center gap-1.5 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--fg)]"
      >
        {value ? (
          <>
            {selectedIcon ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={selectedIcon} alt="" className="h-4 w-4 shrink-0 object-contain" />
            ) : null}
            <span className="max-w-[9rem] truncate">{value}</span>
          </>
        ) : (
          <span className="text-[var(--muted)]">전체 소나타</span>
        )}
        <ChevronDown className="h-3.5 w-3.5 shrink-0 text-[var(--muted)]" aria-hidden="true" />
      </button>
      {open ? (
        <div className="absolute left-0 z-30 mt-1 max-h-72 w-64 overflow-y-auto rounded-md border border-[var(--line)] bg-[var(--surface)] p-1 shadow-xl">
          <button
            type="button"
            onClick={() => {
              onChange("");
              setOpen(false);
            }}
            className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] ${
              value ? "text-[var(--fg-soft)]" : "bg-[var(--surface-2)] text-[var(--fg)]"
            }`}
          >
            <span className="h-5 w-5 shrink-0" />
            전체 소나타
          </button>
          {options.map((name) => {
            const icon = imageSrc(iconOf(name));
            return (
              <button
                key={name}
                type="button"
                onClick={() => {
                  onChange(name);
                  setOpen(false);
                }}
                className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-[var(--surface-2)] ${
                  value === name ? "bg-[var(--surface-2)] text-[var(--fg)]" : "text-[var(--fg-soft)]"
                }`}
              >
                {icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={icon} alt="" className="h-5 w-5 shrink-0 object-contain" />
                ) : (
                  <span className="h-5 w-5 shrink-0" />
                )}
                <span className="truncate">{name}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

/** A single grid cell: rarity-ringed icon, truncated name, and a small hint. */
function GridCell({
  name,
  image,
  rarity,
  hint,
  onClick,
}: {
  name: string;
  image?: string | null;
  rarity?: number | null;
  hint?: string;
  onClick: () => void;
}) {
  const src = imageSrc(image);
  return (
    <button
      type="button"
      onClick={onClick}
      title={`${name} 상세 보기`}
      className="flex flex-col items-center gap-1.5 rounded-md p-1.5 text-center transition hover:-translate-y-0.5 hover:bg-[var(--surface-2)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          className={`h-16 w-16 rounded-md border border-[var(--line)] bg-[var(--surface-2)] object-contain shadow-sm ring-2 ${rarityRing(rarity)}`}
        />
      ) : (
        <span
          className={`inline-flex h-16 w-16 items-center justify-center rounded-md border border-[var(--line)] bg-[var(--surface-2)] text-sm font-semibold text-[var(--fg-soft)] shadow-sm ring-2 ${rarityRing(rarity)}`}
        >
          {name.slice(0, 2)}
        </span>
      )}
      <span className="w-full truncate text-xs font-medium text-[var(--fg)]">{name}</span>
      {hint ? <span className="w-full truncate text-[11px] text-[var(--muted)]">{hint}</span> : null}
    </button>
  );
}

export function Codex() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<SubTab>("resonators");
  const [resonators, setResonators] = useState<CodexResonator[]>([]);
  const [weapons, setWeapons] = useState<CodexWeapon[]>([]);
  const [echoes, setEchoes] = useState<CodexEcho[]>([]);
  const [sonataSets, setSonataSets] = useState<SonataSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);

  const [search, setSearch] = useState("");
  // Resonator filters
  const [element, setElement] = useState("");
  const [weaponTypeR, setWeaponTypeR] = useState("");
  const [rarityR, setRarityR] = useState("");
  const [role, setRole] = useState("");
  // Weapon filters
  const [weaponTypeW, setWeaponTypeW] = useState("");
  const [rarityW, setRarityW] = useState("");
  // Echo filters
  const [cost, setCost] = useState("");
  const [sonata, setSonata] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getCodexResonators(), getCodexWeapons(), getCodexEchoes(), getSonataSets()])
      .then(([res, wep, ech, son]) => {
        if (cancelled) return;
        setResonators(res);
        setWeapons(wep);
        setEchoes(ech);
        setSonataSets(son);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!detail) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDetail(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detail]);

  const tElement = (value?: string | null) =>
    value ? (t.elements as Record<string, string>)[value] ?? value : value ?? "";

  // Distinct filter option lists derived from the loaded data.
  const elementOptions = useMemo(
    () => Array.from(new Set(resonators.map((r) => r.element).filter(Boolean))).sort() as string[],
    [resonators],
  );
  const resonatorWeaponTypes = useMemo(
    () => Array.from(new Set(resonators.map((r) => r.weapon_type_ko).filter(Boolean))).sort() as string[],
    [resonators],
  );
  const resonatorRarities = useMemo(
    () => Array.from(new Set(resonators.map((r) => r.rarity).filter(Boolean))).sort((a, b) => b - a).map(String),
    [resonators],
  );
  const roleOptions = useMemo(
    () => Array.from(new Set(resonators.map((r) => r.role).filter(Boolean))) as Role[],
    [resonators],
  );
  const weaponTypeOptions = useMemo(
    () => Array.from(new Set(weapons.map((w) => w.weapon_type_ko).filter(Boolean))).sort() as string[],
    [weapons],
  );
  const weaponRarities = useMemo(
    () => Array.from(new Set(weapons.map((w) => w.rarity).filter(Boolean))).sort((a, b) => b - a).map(String),
    [weapons],
  );
  const costOptions = useMemo(
    () => Array.from(new Set(echoes.map((e) => e.cost).filter((c) => c != null))).sort((a, b) => a - b).map(String),
    [echoes],
  );
  const sonataOptions = useMemo(
    () => Array.from(new Set(echoes.flatMap((e) => e.sonata ?? []).filter(Boolean))).sort(),
    [echoes],
  );
  const sonataIcon = useMemo(() => {
    const map = new Map<string, string>();
    for (const set of sonataSets) if (set.name_ko && set.icon) map.set(set.name_ko, set.icon);
    return map;
  }, [sonataSets]);

  const query = search.trim().toLowerCase();

  const filteredResonators = useMemo(() => {
    return resonators.filter((r) => {
      const matchesSearch =
        !query ||
        r.name.toLowerCase().includes(query) ||
        (r.name_en ?? "").toLowerCase().includes(query);
      return (
        matchesSearch &&
        (!element || r.element === element) &&
        (!weaponTypeR || r.weapon_type_ko === weaponTypeR) &&
        (!rarityR || String(r.rarity) === rarityR) &&
        (!role || r.role === role)
      );
    });
  }, [resonators, query, element, weaponTypeR, rarityR, role]);

  const filteredWeapons = useMemo(() => {
    return weapons.filter((w) => {
      const matchesSearch =
        !query ||
        w.name_ko.toLowerCase().includes(query) ||
        (w.name_en ?? "").toLowerCase().includes(query);
      return (
        matchesSearch &&
        (!weaponTypeW || w.weapon_type_ko === weaponTypeW) &&
        (!rarityW || String(w.rarity) === rarityW)
      );
    });
  }, [weapons, query, weaponTypeW, rarityW]);

  const filteredEchoes = useMemo(() => {
    return echoes.filter((e) => {
      const matchesSearch =
        !query ||
        e.name_ko.toLowerCase().includes(query) ||
        (e.name_en ?? "").toLowerCase().includes(query);
      return (
        matchesSearch &&
        (!cost || String(e.cost) === cost) &&
        (!sonata || (e.sonata ?? []).includes(sonata))
      );
    });
  }, [echoes, query, cost, sonata]);

  // Echoes are shown grouped by sonata set; an echo appears under each of its sets.
  // encore lists a monster's echo as several id/rarity variants, so within a set we
  // dedupe by name (keeping the highest-rarity record) — one card per echo per set.
  const echoGroups = useMemo(() => {
    const groups = new Map<string, Map<string, CodexEcho>>();
    const noSet = new Map<string, CodexEcho>();
    const keepBetter = (bucket: Map<string, CodexEcho>, e: CodexEcho) => {
      const cur = bucket.get(e.name_ko);
      if (!cur || (e.rarity ?? 0) > (cur.rarity ?? 0)) bucket.set(e.name_ko, e);
    };
    for (const e of filteredEchoes) {
      const sets = (e.sonata ?? []).filter(Boolean);
      if (sets.length === 0) keepBetter(noSet, e);
      for (const s of sets) {
        let bucket = groups.get(s);
        if (!bucket) groups.set(s, (bucket = new Map()));
        keepBetter(bucket, e);
      }
    }
    // When a sonata is selected in the filter, show only that set's group.
    const names = sonata ? [sonata] : sonataOptions;
    const ordered = names
      .map((name) => ({ name, echoes: [...(groups.get(name)?.values() ?? [])] }))
      .filter((g) => g.echoes.length > 0);
    if (!sonata && noSet.size) ordered.push({ name: "", echoes: [...noSet.values()] });
    return ordered;
  }, [filteredEchoes, sonataOptions, sonata]);

  const count =
    tab === "resonators"
      ? filteredResonators.length
      : tab === "weapons"
        ? filteredWeapons.length
        : filteredEchoes.length;

  return (
    <section className="grid gap-4">
      <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 shadow-panel">
        {/* Sub-tab switcher */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            aria-pressed={tab === "resonators"}
            onClick={() => setTab("resonators")}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${subTabClass(tab === "resonators")}`}
          >
            <UserRound className="h-4 w-4" aria-hidden="true" />
            캐릭터
          </button>
          <button
            type="button"
            aria-pressed={tab === "weapons"}
            onClick={() => setTab("weapons")}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${subTabClass(tab === "weapons")}`}
          >
            <Swords className="h-4 w-4" aria-hidden="true" />
            무기
          </button>
          <button
            type="button"
            aria-pressed={tab === "echoes"}
            onClick={() => setTab("echoes")}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium transition ${subTabClass(tab === "echoes")}`}
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            에코
          </button>
        </div>

        {/* Filter bar */}
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <input
            className="min-h-9 rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-3 py-1.5 text-sm text-[var(--fg)] placeholder:text-[var(--muted)]"
            placeholder="이름 검색"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          {tab === "resonators" ? (
            <>
              <FilterSelect label="전체 속성" value={element} onChange={setElement} options={elementOptions} render={tElement} />
              <FilterSelect label="전체 무기" value={weaponTypeR} onChange={setWeaponTypeR} options={resonatorWeaponTypes} />
              <FilterSelect label="전체 성급" value={rarityR} onChange={setRarityR} options={resonatorRarities} render={(v) => `${v}★`} />
              <FilterSelect label="전체 역할" value={role} onChange={setRole} options={roleOptions} render={(v) => ROLE_LABELS[v as Role] ?? v} />
            </>
          ) : null}
          {tab === "weapons" ? (
            <>
              <FilterSelect label="전체 종류" value={weaponTypeW} onChange={setWeaponTypeW} options={weaponTypeOptions} />
              <FilterSelect label="전체 성급" value={rarityW} onChange={setRarityW} options={weaponRarities} render={(v) => `${v}★`} />
            </>
          ) : null}
          {tab === "echoes" ? (
            <>
              <FilterSelect label="전체 코스트" value={cost} onChange={setCost} options={costOptions} render={(v) => `${v} 코스트`} />
              <SonataFilter
                value={sonata}
                onChange={setSonata}
                options={sonataOptions}
                iconOf={(name) => sonataIcon.get(name)}
              />
            </>
          ) : null}
        </div>

        {error ? (
          <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p>
        ) : null}
      </div>

      {loading ? (
        <div className="rounded-lg border border-dashed border-[var(--line-2)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">
          {t.app.loading}…
        </div>
      ) : count === 0 ? (
        <div className="rounded-lg border border-dashed border-[var(--line-2)] bg-[var(--surface)] p-8 text-center text-sm text-[var(--muted)]">
          {t.planner.noResults}
        </div>
      ) : tab === "echoes" ? (
        <div className="grid gap-4">
          {echoGroups.map((group) => (
            <div key={group.name || "_none"} className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 shadow-panel">
              <div className="mb-3 flex items-center gap-2">
                {group.name && sonataIcon.get(group.name) ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={imageSrc(sonataIcon.get(group.name))} alt="" className="h-6 w-6 shrink-0 object-contain" />
                ) : null}
                <h3 className="text-sm font-semibold text-[var(--fg)]">{group.name || "기타"}</h3>
                <span className="text-xs text-[var(--muted)]">{group.echoes.length}</span>
              </div>
              <div className={GRID_CLASS}>
                {group.echoes.map((item) => (
                  <GridCell
                    key={item.id}
                    name={item.name_ko}
                    image={item.icon}
                    rarity={item.rarity}
                    hint={item.cost != null ? `${item.cost} 코스트` : ""}
                    onClick={() => setDetail({ type: "echo", item })}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4 shadow-panel">
          <div className={GRID_CLASS}>
            {tab === "resonators"
              ? filteredResonators.map((item) => (
                  <GridCell
                    key={item.id}
                    name={item.name}
                    image={item.image}
                    rarity={item.rarity}
                    hint={tElement(item.element)}
                    onClick={() => setDetail({ type: "resonator", item })}
                  />
                ))
              : null}
            {tab === "weapons"
              ? filteredWeapons.map((item) => (
                  <GridCell
                    key={item.id}
                    name={item.name_ko}
                    image={item.icon}
                    rarity={item.rarity}
                    hint={item.weapon_type_ko ?? ""}
                    onClick={() => setDetail({ type: "weapon", item })}
                  />
                ))
              : null}
          </div>
        </div>
      )}

      {detail ? (
        <Portal>
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
            role="dialog"
            aria-modal="true"
            onClick={() => setDetail(null)}
          >
          <div
            className="relative max-h-[85vh] w-full max-w-md overflow-y-auto rounded-lg border border-[var(--line)] bg-[var(--surface)] p-5 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setDetail(null)}
              aria-label="닫기"
              className="absolute right-3 top-3 rounded-md p-1 text-[var(--muted)] transition hover:bg-[var(--surface-2)] hover:text-[var(--fg)]"
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>

            {detail.type === "resonator" ? (
              <ResonatorDetail item={detail.item} tElement={tElement} />
            ) : detail.type === "weapon" ? (
              <WeaponDetail item={detail.item} />
            ) : (
              <EchoDetail item={detail.item} />
            )}
          </div>
          </div>
        </Portal>
      ) : null}
    </section>
  );
}

function DetailHeader({
  name,
  image,
  rarity,
  meta,
}: {
  name: string;
  image?: string | null;
  rarity?: number | null;
  meta: string;
}) {
  const src = imageSrc(image);
  return (
    <div className="flex items-center gap-3">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          className={`h-20 w-20 shrink-0 rounded-md border border-[var(--line)] bg-[var(--surface-2)] object-contain ring-2 ${rarityRing(rarity)}`}
        />
      ) : null}
      <div className="min-w-0">
        <h3 className="text-lg font-semibold text-[var(--fg)]">{name}</h3>
        <p className="mt-1 text-sm text-[var(--muted)]">{meta}</p>
      </div>
    </div>
  );
}

export function ResonatorDetail({
  item,
  tElement,
}: {
  item: CodexResonator;
  tElement: (value?: string | null) => string;
}) {
  const meta = [
    item.rarity ? `${item.rarity}★` : null,
    tElement(item.element) || null,
    item.weapon_type_ko || null,
    ROLE_LABELS[item.role] ?? item.role,
  ]
    .filter(Boolean)
    .join(" · ");

  const chainNodes = (item.resonance_chain ?? [])
    .map((node) => node.NodeName)
    .filter(Boolean) as string[];

  const maxLevel = item.max_level ?? 90;
  const [level, setLevel] = useState(maxLevel);
  const curves = item.stat_curves ?? null;
  const statValue = (key: string): number | undefined => {
    const curve = curves?.[key];
    if (curve?.length) {
      return (curve.find((c) => c.level === level) ?? curve[curve.length - 1])?.value;
    }
    return item.stats?.[key];
  };
  const fmtStat = (key: string, value: number): string =>
    key === "Crit" || key === "CritDamage"
      ? `${Number(value).toFixed(1)}%`
      : Math.round(Number(value)).toLocaleString();
  const stats = STAT_KEYS.map((key) => ({ key, value: statValue(key) })).filter(
    (entry) => entry.value != null,
  );

  return (
    <div className="grid gap-4">
      <DetailHeader name={item.name} image={item.image} rarity={item.rarity} meta={meta} />

      {item.skills?.length ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">스킬</h4>
          <ul className="grid gap-2">
            {item.skills.map((skill, index) => (
              <li key={`${skill.SkillName ?? "skill"}-${index}`} className="text-sm">
                {skill.SkillName ? (
                  <span className="font-semibold text-[var(--fg)]">{stripTags(skill.SkillName)}</span>
                ) : null}
                {skill.SkillDescribe ? (
                  <p className="mt-0.5 line-clamp-4 text-[var(--fg-soft)]">{stripTags(skill.SkillDescribe)}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {chainNodes.length ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">공명 사슬</h4>
          <ol className="grid gap-1 text-sm text-[var(--fg-soft)]">
            {chainNodes.map((node, index) => (
              <li key={`${node}-${index}`}>
                <span className="mr-1.5 text-[var(--muted)]">S{index + 1}</span>
                {stripTags(node)}
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {stats.length ? (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-[var(--fg)]">스탯</h4>
            {curves ? <span className="text-xs text-[var(--muted)]">Lv. {level}</span> : null}
          </div>
          {curves ? (
            <input
              type="range"
              min={1}
              max={maxLevel}
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="mb-3 w-full accent-[var(--accent)]"
              aria-label="레벨"
            />
          ) : null}
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {stats.map((entry) => (
              <div key={entry.key} className="flex items-center justify-between rounded-md bg-[var(--surface-2)] px-2.5 py-1.5">
                <dt className="text-[var(--muted)]">{STAT_LABELS[entry.key]}</dt>
                <dd className="font-medium text-[var(--fg)]">{fmtStat(entry.key, entry.value as number)}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}
    </div>
  );
}

export function WeaponDetail({ item }: { item: CodexWeapon }) {
  const meta = [item.rarity ? `${item.rarity}★` : null, item.weapon_type_ko || null]
    .filter(Boolean)
    .join(" · ");
  const resonanceName = weaponResonanceName(item);
  const desc = stripTags(item.desc);
  const lore = stripTags(item.attributes_description);

  const props = (item.properties ?? []).filter((p) => p?.curve?.length || p?.max != null);
  const maxLevel = props[0]?.curve?.at(-1)?.level ?? 90;
  const [level, setLevel] = useState(maxLevel);
  const propAt = (p: NonNullable<CodexWeapon["properties"]>[number]): number | undefined => {
    if (p.curve?.length) return (p.curve.find((c) => c.level === level) ?? p.curve.at(-1))?.value;
    return p.max ?? undefined;
  };

  return (
    <div className="grid gap-4">
      <DetailHeader name={item.name_ko} image={item.icon} rarity={item.rarity} meta={meta} />

      {props.length ? (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-[var(--fg)]">스탯</h4>
            <span className="text-xs text-[var(--muted)]">Lv. {level}</span>
          </div>
          <input
            type="range"
            min={1}
            max={maxLevel}
            value={level}
            onChange={(e) => setLevel(Number(e.target.value))}
            className="mb-3 w-full accent-[var(--accent)]"
            aria-label="레벨"
          />
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {props.map((p, i) => {
              const v = propAt(p);
              if (v == null) return null;
              return (
                <div key={i} className="flex items-center justify-between rounded-md bg-[var(--surface-2)] px-2.5 py-1.5">
                  <dt className="text-[var(--muted)]">{p.name}</dt>
                  <dd className="font-medium text-[var(--fg)]">
                    {i === 0 ? Math.round(Number(v)).toLocaleString() : `${Number(v).toFixed(1)}%`}
                  </dd>
                </div>
              );
            })}
          </dl>
        </div>
      ) : null}

      {resonanceName || desc ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">패시브{resonanceName ? ` · ${resonanceName}` : ""}</h4>
          {desc ? <p className="text-sm text-[var(--fg-soft)]">{desc}</p> : null}
        </div>
      ) : null}

      {lore ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">설명</h4>
          <p className="line-clamp-5 text-sm text-[var(--muted)]">{lore}</p>
        </div>
      ) : null}
    </div>
  );
}

function EchoDetail({ item }: { item: CodexEcho }) {
  const meta = [item.cost != null ? `${item.cost} 코스트` : null, item.rarity ? `${item.rarity}★` : null]
    .filter(Boolean)
    .join(" · ");
  const skillDesc = stripTags(item.skill?.DescriptionEx);

  return (
    <div className="grid gap-4">
      <DetailHeader name={item.name_ko} image={item.icon} rarity={item.rarity} meta={meta} />

      {item.sonata?.length ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">소나타</h4>
          <div className="flex flex-wrap gap-1.5">
            {item.sonata.map((name) => (
              <span
                key={name}
                className="rounded-md border border-[var(--line-2)] bg-[var(--surface-2)] px-2 py-1 text-xs text-[var(--fg-soft)]"
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {skillDesc ? (
        <div>
          <h4 className="mb-1.5 text-sm font-semibold text-[var(--fg)]">스킬</h4>
          <p className="text-sm text-[var(--fg-soft)]">{skillDesc}</p>
        </div>
      ) : null}
    </div>
  );
}
