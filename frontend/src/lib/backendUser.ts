// 저장 시점 self-heal: ai_recommendations.user_id 는 users(id) FK 이므로,
// 검증된 세션 신원을 백엔드 users 테이블에 upsert 해 두어야 저장이 FK 위반 없이 통과한다.
// 로그인 동기화(auth.ts jwt 콜백)는 최초 로그인(account 존재) 시에만 돌기 때문에,
// 세션은 유효하지만 users 행이 없는 경우(테이블 초기화 등)를 이 함수로 보정한다.

const INTERNAL_BASE_URL = process.env.INTERNAL_API_BASE_URL ?? "http://127.0.0.1:8000";

/**
 * 세션 사용자를 백엔드 users 테이블에 upsert. 성공 시 true.
 * INTERNAL_API_SECRET 미설정 또는 요청 실패 시 false(호출부에서 저장 중단 판단).
 */
export async function ensureBackendUser(params: {
  email: string;
  name?: string | null;
  image?: string | null;
  role?: string | null;
}): Promise<boolean> {
  const internalSecret = process.env.INTERNAL_API_SECRET;
  if (!internalSecret) {
    console.error("INTERNAL_API_SECRET 미설정 — 저장 전 사용자 동기화를 건너뜀");
    return false;
  }
  try {
    const res = await fetch(`${INTERNAL_BASE_URL}/auth/sync-user`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Internal-Secret": internalSecret },
      body: JSON.stringify({
        email: params.email,
        name: params.name ?? null,
        image: params.image ?? null,
        role: params.role === "admin" ? "admin" : "user",
        provider: "google",
        provider_account_id: params.email,
      }),
      cache: "no-store",
    });
    return res.ok;
  } catch (error) {
    console.error("저장 전 사용자 동기화 실패", error);
    return false;
  }
}
