import type { NextConfig } from "next";

const backendOrigin = process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: __dirname,
  async rewrites() {
    return [
      // 기록 API(/backend/ai/recommendations[/...])는 인증 라우트 핸들러가 처리한다.
      // 이 catch-all 프록시에서 제외하지 않으면 afterFiles rewrite가 동적 [id] 라우트보다
      // 먼저 백엔드로 우회시켜 인증/소유권 검사를 건너뛴다(경로기반 DELETE 우회).
      {
        source: "/backend/:path((?!ai/recommendations(?:/|$)).*)",
        destination: `${backendOrigin}/:path`,
      },
    ];
  },
};

export default nextConfig;
