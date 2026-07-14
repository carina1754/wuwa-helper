// BYO NVIDIA 키/모델은 서버에 저장하지 않고 브라우저 localStorage 에만 둔다.
// API 호출 시 X-LLM-Key / X-LLM-Model 헤더로 실어 보낸다(본문/기록엔 안 섞임).
export const NVIDIA_KEY_STORAGE = "nvidia_api_key";
export const NVIDIA_MODEL_STORAGE = "nvidia_model";

export function getNvidiaKey(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(NVIDIA_KEY_STORAGE) ?? "";
}

export function getNvidiaModel(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(NVIDIA_MODEL_STORAGE) ?? "";
}

export function setNvidiaKey(value: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(NVIDIA_KEY_STORAGE, value.trim());
}

export function setNvidiaModel(value: string): void {
  if (typeof window !== "undefined") window.localStorage.setItem(NVIDIA_MODEL_STORAGE, value);
}
