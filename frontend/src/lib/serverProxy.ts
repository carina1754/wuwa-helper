import { auth } from "@/auth";

// /backend/* 리라이트는 무인증 공개 프록시다. 세션 검증이 필요한 백엔드 경로는
// 여기 헬퍼로 라우트 핸들러에서 가드한 뒤에만 서버-사이드로 전달한다.
// (ai/recommendations 핸들러와 동일한 패턴의 공용화)

export const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export async function sessionUser() {
  const session = await auth();
  return session?.user ?? null;
}

export async function isAdmin(): Promise<boolean> {
  const user = await sessionUser();
  return user?.role === "admin";
}

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export async function passthrough(res: Response): Promise<Response> {
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
