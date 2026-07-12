import type { Metadata } from "next";
import GuideContent from "@/components/GuideContent";

export const metadata: Metadata = {
  title: "이용 가이드 — 띵조 AI",
  description: "띵조 AI 사용법: 도감, 픽업 일정표, 파티 딜 계산(풀 업타임·자동 팀 버프), AI 빌딩까지 스크린샷과 함께 안내합니다.",
};

export default function GuidePage() {
  return <GuideContent />;
}
