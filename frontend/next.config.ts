import type { NextConfig } from "next";

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: __dirname,
  async rewrites() {
    return [
      // 인증 라우트 핸들러가 처리하는 경로는 catch-all 프록시에서 제외한다.
      // 제외하지 않으면 afterFiles rewrite가 동적 라우트보다 먼저 백엔드로 우회시켜
      // 인증/소유권/관리자 검사를 건너뛴다(경로기반 우회).
      //  - ai/recommendations[/...]: 세션 강제 + 소유권 검사
      //  - ai/chat: 로그인 세션 강제(익명 LLM 호출 차단)
      //  - rules / import / export: 관리자 세션 강제(무인증 공개 쓰기·덤프 차단)
      {
        source: "/backend/:path((?!ai/recommendations(?:/|$)|ai/chat$|rules$|import$|export$).*)",
        destination: `${backendOrigin}/:path`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
