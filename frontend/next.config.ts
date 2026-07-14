import type { NextConfig } from "next";

// 단일 프로세스 스탠드얼론 배포: 정적 export를 FastAPI가 서빙.
// rewrites/headers 는 static export 미지원 → 제거(보안 헤더는 배포 프록시/서버가 담당).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true, // /guide/ → guide/index.html 로 StaticFiles(html=True) 서빙
  images: { unoptimized: true },
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
