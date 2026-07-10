import { NextRequest } from "next/server";
import { BACKEND_ORIGIN, isAdmin, json, passthrough } from "@/lib/serverProxy";

// 빌드 규칙 조회/저장은 관리자 화면(RulesManager) 전용이다.
// catch-all 리라이트로 그대로 흘리면 POST /backend/rules 가 무인증 공개 쓰기가 되므로
// 여기서 관리자 세션을 강제한 뒤에만 백엔드로 전달한다.

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  if (!(await isAdmin())) return json(403, { detail: "관리자 권한이 필요합니다." });
  return passthrough(await fetch(`${BACKEND_ORIGIN}/rules`, { cache: "no-store" }));
}

export async function POST(req: NextRequest): Promise<Response> {
  if (!(await isAdmin())) return json(403, { detail: "관리자 권한이 필요합니다." });
  const body = await req.text();
  return passthrough(
    await fetch(`${BACKEND_ORIGIN}/rules`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      cache: "no-store",
    }),
  );
}
