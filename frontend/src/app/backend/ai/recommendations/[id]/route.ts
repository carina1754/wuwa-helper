import { NextRequest } from "next/server";
import { auth } from "@/auth";
import { accountIdFromEmail } from "@/lib/accountId";

// 개별 기록 조회/삭제는 세션 계정 소유 레코드에만 허용한다.
// 백엔드 DELETE는 소유권 검사가 없으므로, 여기서 먼저 소유 여부를 확인한 뒤에만 통과시킨다.

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

/** 대상 레코드의 소유권을 검증. 200=소유, 그 외는 거부 상태코드. */
async function ownershipStatus(id: string, accountId: string): Promise<number> {
  const res = await fetch(`${BACKEND_ORIGIN}/ai/recommendations/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (res.status === 404) return 404;
  if (!res.ok) return res.status;
  const record = (await res.json()) as { user_id?: string | null };
  return record?.user_id === accountId ? 200 : 403;
}

export async function GET(_req: NextRequest, ctx: { params: Promise<{ id: string }> }): Promise<Response> {
  const email = await sessionEmail();
  if (!email) return json(401, { detail: "로그인이 필요합니다." });
  const accountId = accountIdFromEmail(email);
  const { id } = await ctx.params;
  const res = await fetch(`${BACKEND_ORIGIN}/ai/recommendations/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (res.status === 404) return json(404, { detail: "기록을 찾을 수 없습니다." });
  if (!res.ok) {
    const text = await res.text();
    return new Response(text, { status: res.status, headers: { "content-type": "application/json" } });
  }
  const record = (await res.json()) as { user_id?: string | null };
  if (record?.user_id !== accountId) return json(403, { detail: "권한이 없습니다." });
  return json(200, record);
}

export async function DELETE(_req: NextRequest, ctx: { params: Promise<{ id: string }> }): Promise<Response> {
  const email = await sessionEmail();
  if (!email) return json(401, { detail: "로그인이 필요합니다." });
  const accountId = accountIdFromEmail(email);
  const { id } = await ctx.params;
  const owned = await ownershipStatus(id, accountId);
  if (owned !== 200) {
    return json(owned, { detail: owned === 403 ? "권한이 없습니다." : "기록을 찾을 수 없습니다." });
  }
  const res = await fetch(`${BACKEND_ORIGIN}/ai/recommendations/${encodeURIComponent(id)}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (res.status === 204) return new Response(null, { status: 204 });
  const text = await res.text();
  return new Response(text, { status: res.status, headers: { "content-type": "application/json" } });
}
