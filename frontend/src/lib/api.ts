import { API_BASE_URL } from "./constants";
import { getNvidiaKey, getNvidiaModel } from "./settings";
import type {
  AiChatResponse,
  AiMessage,
  AiProfile,
  AiRecommendationCreate,
  AiRecommendationRecord,
  CodexEcho,
  CodexResonator,
  CodexWeapon,
  GameUpdateSummary,
  PickupBanner,
  SonataSet,
  SiteUpdateEntry,
  TeamCalcRequestBody,
  TeamCalcResult,
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

/** BYO 키/모델을 헤더로 실어 보낸다. 없으면 서버가 mock/기본값으로 폴백. */
function aiHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const key = getNvidiaKey();
  const model = getNvidiaModel();
  if (key) headers["X-LLM-Key"] = key;
  if (model) headers["X-LLM-Model"] = model;
  return headers;
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

/** BYO 키로 NVIDIA(OpenAI 호환) 채팅 모델 목록 조회. */
export function getModels(): Promise<string[]> {
  return request("/ai/models", { headers: aiHeaders() });
}

export function aiChat(messages: AiMessage[], profile: AiProfile): Promise<AiChatResponse> {
  return request("/ai/chat", {
    method: "POST",
    headers: aiHeaders({ "Content-Type": "application/json" }),
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

export async function deleteRecommendation(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/ai/recommendations/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(text || "삭제에 실패했습니다.", response.status);
  }
}
