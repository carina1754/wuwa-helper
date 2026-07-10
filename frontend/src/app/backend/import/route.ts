import { NextRequest } from "next/server";
import { BACKEND_ORIGIN, isAdmin, json, passthrough } from "@/lib/serverProxy";

// /import 는 규칙·캐릭터·기록을 덮어쓰는 뮤테이션이라 무인증 공개 시 DB 주입이 된다.
// 관리자 화면(SettingsPanel) 전용이므로 관리자 세션을 강제한다.

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest): Promise<Response> {
  if (!(await isAdmin())) return json(403, { detail: "관리자 권한이 필요합니다." });
  const body = await req.text();
  return passthrough(
    await fetch(`${BACKEND_ORIGIN}/import`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      cache: "no-store",
    }),
  );
}
