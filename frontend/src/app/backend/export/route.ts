import { BACKEND_ORIGIN, isAdmin, json, passthrough } from "@/lib/serverProxy";

// /export 는 규칙·캐릭터·기록 전체 덤프라 무인증 공개 시 데이터 유출이다.
// 관리자 화면(SettingsPanel) 전용이므로 관리자 세션을 강제한다.

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  if (!(await isAdmin())) return json(403, { detail: "관리자 권한이 필요합니다." });
  return passthrough(await fetch(`${BACKEND_ORIGIN}/export`, { cache: "no-store" }));
}
