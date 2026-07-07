"use client";

import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

/**
 * Renders children into <body> via a portal.
 *
 * 왜 필요한가: 탭 뷰(`.view.on > *`)에 걸린 진입 애니메이션 `rise`(globals.css)가
 * `transform` 키프레임을 `animation-fill-mode: both`로 유지한다. Chromium에서 이는
 * 해당 요소를 `position: fixed` 자손의 containing block으로 만든다. 그 서브트리 안의
 * `fixed inset-0` 오버레이는 뷰포트가 아니라 (세로로 긴) 섹션 박스 기준으로 잡혀서,
 * 가운데 정렬된 모달 패널이 화면 밖으로 밀려 "검은 배경만 보이고 팝업은 안 뜨는" 증상이 난다.
 * 모달을 <body>로 포탈하면 애니메이션 조상 밖으로 빠져나와 이 문제를 피한다.
 */
export function Portal({ children }: { children: ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return createPortal(children, document.body);
}
