import { API_BASE_URL } from "./constants";
import type {
  AiChatResponse,
  AiMessage,
  AiProfile,
  AiRecommendationCreate,
  AiRecommendationRecord,
  AnalysisSession,
  AnalyzeResponse,
  BuildRule,
  CharacterSnapshot,
  CodexEcho,
  CodexResonator,
  CodexWeapon,
  GameUpdateSummary,
  PickupBanner,
  PickupScheduleItem,
  Role,
  SonataSet,
  SiteUpdateEntry,
  SnapshotDamageRequestBody,
  SnapshotDamageResult,
  TeamCalcRequestBody,
  TeamCalcResult,
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

export function getPickupSchedule(year?: number): Promise<PickupScheduleItem[]> {
  const params = year ? `?year=${year}` : "";
  return request(`/pickup-schedule${params}`);
}

export function getPickupBanners(): Promise<PickupBanner[]> {
  return request("/pickup-banners");
}

export function getCodexResonators(): Promise<CodexResonator[]> {
  return request("/codex/resonators");
}

export function getCodexWeapons(): Promise<CodexWeapon[]> {
  return request("/codex/weapons");
}

export function getCodexEchoes(): Promise<CodexEcho[]> {
  return request("/codex/echoes");
}

export function getSonataSets(): Promise<SonataSet[]> {
  return request("/sonata-sets");
}

export function getUpdates(): Promise<GameUpdateSummary[]> {
  return request("/updates");
}

export function getSiteUpdates(): Promise<SiteUpdateEntry[]> {
  return request("/site-updates");
}

export function getGameConfig(): Promise<Record<string, unknown>> {
  return request("/game-config");
}

// Server-side party damage from real builds (our engine, not phro's default assumptions).
export function teamCalculate(body: TeamCalcRequestBody): Promise<TeamCalcResult> {
  return request("/sim/team-calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Absolute damage from a real-account OCR snapshot — the "내 실제 빌드 기준" differentiator.
export function snapshotDamage(body: SnapshotDamageRequestBody): Promise<SnapshotDamageResult> {
  return request("/sim/snapshot-damage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

export function aiChat(messages: AiMessage[], profile: AiProfile): Promise<AiChatResponse> {
  return request("/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, profile }),
  });
}

export function saveRecommendation(payload: AiRecommendationCreate): Promise<AiRecommendationRecord> {
  return request("/ai/recommendations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function getRecommendations(userId?: string): Promise<AiRecommendationRecord[]> {
  const params = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request(`/ai/recommendations${params}`);
}

export function getRecommendation(id: string): Promise<AiRecommendationRecord> {
  return request(`/ai/recommendations/${id}`);
}

export async function deleteRecommendation(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/ai/recommendations/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || "삭제에 실패했습니다.", response.status);
  }
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
