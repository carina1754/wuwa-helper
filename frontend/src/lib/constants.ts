import type { CharacterSnapshot, EchoItem } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Resolve a stored image path: absolute URLs pass through; our locally-cached
 * paths (e.g. "/catalog/image/...") are prefixed with the API base. */
export function mediaUrl(path?: string | null): string | undefined {
  if (!path) return undefined;
  return path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
}

export const TABS = ["Ai", "Planner", "PickupSchedule", "Updates", "Teams", "Snapshot", "History"] as const;
export type AppTab = (typeof TABS)[number] | "SiteUpdates";

export function emptyEcho(slot: number): EchoItem {
  return {
    name: "",
    slot: String(slot),
    set_name: "",
    cost: null,
    level: null,
    main_stat: "",
    sub_stats: [
      { name: "", value: "" },
      { name: "", value: "" },
      { name: "", value: "" },
    ],
  };
}

export function emptySnapshot(): CharacterSnapshot {
  return {
    character_name: "",
    character_level: null,
    role: "main_dps",
    weapon: { name: "", level: null, rank: null, main_stat: "" },
    stats: {},
    echoes: [1, 2, 3, 4, 5].map(emptyEcho),
    raw_text: "",
  };
}
