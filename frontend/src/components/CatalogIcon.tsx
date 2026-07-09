"use client";

import { useState } from "react";
import { mediaUrl } from "@/lib/constants";

type CatalogKind = "resonator" | "weapon" | "echo";

// 프론트 종류 → 백엔드 이미지 kind(/catalog/image/{kind}/{id}).
const KIND_PATH: Record<CatalogKind, string> = {
  resonator: "characters",
  weapon: "weapons",
  echo: "echoes",
};

/** 카탈로그(도감) 아이콘을 id만으로 렌더. 이미지가 없으면 이름/물음표 플레이스홀더. */
export function CatalogIcon({
  kind,
  id,
  label,
  size = 48,
  className = "",
}: {
  kind: CatalogKind;
  id?: string | null;
  label?: string | null;
  size?: number;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = id ? mediaUrl(`/catalog/image/${KIND_PATH[kind]}/${id}`) : undefined;
  const box = { width: size, height: size };

  if (!src || failed) {
    return (
      <div
        style={box}
        className={`flex items-center justify-center rounded-md bg-neutral-800 text-[10px] text-neutral-400 ${className}`}
        title={label ?? id ?? ""}
      >
        {label ? label.slice(0, 2) : "?"}
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={label ?? id ?? ""}
      title={label ?? id ?? ""}
      style={box}
      onError={() => setFailed(true)}
      className={`rounded-md object-contain ${className}`}
    />
  );
}

export default CatalogIcon;
