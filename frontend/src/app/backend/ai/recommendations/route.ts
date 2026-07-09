import { NextRequest } from "next/server";
import { auth } from "@/auth";
import { accountIdFromEmail } from "@/lib/accountId";
import { ensureBackendUser } from "@/lib/backendUser";

// 기록 목록/저장은 클라이언트가 보낸 user_id를 신뢰하지 않는다.
// 서버에서 NextAuth 세션(auth())으로 검증한 이메일을 계정 식별자로 강제 주입한다.
// 이 핸들러가 /backend/ai/recommendations 경로를 가로채므로(rewrites보다 우선),
// 브라우저는 인증 없이 원시 백엔드 기록 API에 도달할 수 없다.

const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

async function sessionEmail(): Promise<string | null> {
  const session = await auth();
  return session?.user?.email ?? null;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function passthrough(res: Response): Promise<Response> {
  const text = await res.text();
  return new Response(text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(): Promise<Response> {
  const email = await sessionEmail();
  if (!email) return json(401, { detail: "로그인이 필요합니다." });
  const accountId = accountIdFromEmail(email);
  const res = await fetch(`${BACKEND_ORIGIN}/ai/recommendations?user_id=${encodeURIComponent(accountId)}`, {
    cache: "no-store",
  });
  return passthrough(res);
}

export async function POST(req: NextRequest): Promise<Response> {
  const session = await auth();
  const user = session?.user;
  if (!user?.email) return json(401, { detail: "로그인이 필요합니다." });
  // 저장 전 users 행을 보장(FK). 실패하면 저장은 반드시 500이므로 여기서 중단.
  const synced = await ensureBackendUser({
    email: user.email,
    name: user.name,
    image: user.image,
    role: user.role,
  });
  if (!synced) return json(503, { detail: "계정 동기화에 실패했어요. 잠시 후 다시 시도해 주세요." });
  let payload: Record<string, unknown>;
  try {
    payload = (await req.json()) as Record<string, unknown>;
  } catch {
    payload = {};
  }
  payload.user_id = accountIdFromEmail(user.email); // 클라 값 무시, 세션 이메일→users.id 해시로 강제
  const res = await fetch(`${BACKEND_ORIGIN}/ai/recommendations`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  return passthrough(res);
}
