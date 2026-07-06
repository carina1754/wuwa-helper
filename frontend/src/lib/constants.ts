import type { CharacterSnapshot, EchoItem, Role } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const ROLES: Role[] = ["main_dps", "sub_dps", "support", "healer"];
export const TABS = ["Dashboard", "Analyzer", "Planner", "PickupSchedule", "Updates", "Teams", "History"] as const;
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
