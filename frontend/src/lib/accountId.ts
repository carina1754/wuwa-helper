import { createHash } from "crypto";

// 백엔드 users.id 생성 규칙과 반드시 일치해야 한다(src/users.py _user_id).
// ai_recommendations.user_id 는 users(id) 를 참조하는 FK 이므로,
// 세션 이메일이 아니라 이 해시값을 계정 식별자로 저장/조회한다.
export function accountIdFromEmail(email: string): string {
  return createHash("sha256").update(email.trim().toLowerCase()).digest("hex").slice(0, 32);
}
