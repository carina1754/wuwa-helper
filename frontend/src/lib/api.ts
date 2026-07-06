import { API_BASE_URL } from "./constants";
import type {
  AnalysisSession,
  AnalyzeResponse,
  BuildRule,
  CharacterCatalogItem,
  CharacterSnapshot,
  GameUpdateSummary,
  PickupScheduleItem,
  Role,
  VisionExtractionResult,
} from "./types";

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || `API request failed: ${path}`, response.status);
  }
  return response.json() as Promise<T>;
}

export function health(): Promise<{ ok: boolean }> {
  return request("/health");
}

export function extractVision(file: File): Promise<VisionExtractionResult> {
  const form = new FormData();
  form.append("file", file);
  return request("/vision/extract", { method: "POST", body: form });
}

export function analyzeCharacter(snapshot: CharacterSnapshot, fallbackRole: Role): Promise<AnalyzeResponse> {
  return request("/analyze/character", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ snapshot, fallback_role: fallbackRole }),
  });
}

export function getRules(): Promise<BuildRule[]> {
  return request("/rules");
}

export function getCharacters(): Promise<CharacterCatalogItem[]> {
  return request("/characters");
}

export function getPickupSchedule(year?: number): Promise<PickupScheduleItem[]> {
  const params = year ? `?year=${year}` : "";
  return request(`/pickup-schedule${params}`);
}

export function getUpdates(): Promise<GameUpdateSummary[]> {
  return request("/updates");
}

export function saveRules(rules: BuildRule[]): Promise<BuildRule[]> {
  return request("/rules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rules),
  });
}

export function getHistory(): Promise<AnalysisSession[]> {
  return request("/history");
}

export function saveHistory(session: AnalysisSession): Promise<AnalysisSession> {
  return request("/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(session),
  });
}

export function exportData(): Promise<Record<string, unknown>> {
  return request("/export");
}

export function importData(payload: Record<string, unknown>): Promise<{ rules: number; characters?: number; history: number }> {
  return request("/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
