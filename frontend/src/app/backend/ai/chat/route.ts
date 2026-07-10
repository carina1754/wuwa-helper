import { NextRequest } from "next/server";
import { json, sessionUser } from "@/lib/serverProxy";

// 로컬 추론 LLM은 첫 토큰이 느려 최종 추천 생성에 30초+가 걸린다.
// Next 기본 rewrites 프록시(next.config.ts)는 ~30초에서 요청을 끊어 500(Internal Server Error)을
// 반환하므로, 이 느린 경로만 넉넉한 타임아웃으로 백엔드에 직접 프록시한다.
// 다른 /backend/* 경로(도감·이미지·분석 등 빠른 요청)는 기존 rewrites가 그대로 처리한다.
// UI상 AI 대화는 전부 로그인 후 기능이므로, 익명 호출(LLM 컴퓨트 소모)은 여기서 차단한다.

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
const TIMEOUT_MS = 180_000;

export const maxDuration = 300;
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  if (!(await sessionUser())) return json(401, { detail: "로그인이 필요합니다." });
  const body = await req.text();
  try {
    const res = await fetch(`${BACKEND_ORIGIN}/ai/chat`, {
      method: "POST",
      headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
      body,
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "AI 요청 프록시에 실패했습니다.";
    return new Response(JSON.stringify({ detail: `AI 프록시 오류: ${message}` }), {
      status: 504,
      headers: { "content-type": "application/json" },
    });
  }
}
