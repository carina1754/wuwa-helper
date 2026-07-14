"""content 테이블 → 정적 파일 스냅샷 (스탠드얼론 배포용).

⚠️ content 전용: pickup_schedule / game_updates / site_updates / game_config 만.
   카탈로그(wuwa_*/sonata_set)는 절대 안 건드림 — 카탈로그 정본은 backend/data/catalog/*.json.
   1회 실행(DB 살아있을 때) 후 커밋. 이후 런타임은 이 파일들만 읽음(무DB).
   ORDER BY는 src/content.py 쿼리와 동일(출력 순서 보존).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.database import get_connection  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "content"


def _write(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        cfg = {
            r["id"]: json.loads(r["data_json"])
            for r in conn.execute("SELECT id, data_json FROM game_config").fetchall()
        }
        pickups = [
            json.loads(r["data_json"])
            for r in conn.execute(
                "SELECT data_json FROM pickup_schedule ORDER BY year DESC, month ASC,"
                " CASE category WHEN 'first_pickup' THEN 1 WHEN 'rerun_1' THEN 2"
                " WHEN 'rerun_2' THEN 3 WHEN 'rerun_3' THEN 4 ELSE 5 END"
            ).fetchall()
        ]
        updates = [
            json.loads(r["data_json"])
            for r in conn.execute(
                "SELECT data_json FROM game_updates ORDER BY release_date_kst DESC NULLS LAST, version DESC"
            ).fetchall()
        ]
        site = [
            json.loads(r["data_json"])
            for r in conn.execute(
                "SELECT data_json FROM site_updates ORDER BY date DESC, version DESC NULLS LAST, id DESC"
            ).fetchall()
        ]
        # pickup_banners: 정렬은 런타임(catalog.load_pickup_banners)에서 하므로 순서 무관.
        banners = [
            json.loads(r["data_json"])
            for r in conn.execute("SELECT data_json FROM pickup_banners").fetchall()
        ]
    _write("game_config.json", cfg)
    _write("pickup_schedule.json", pickups)
    _write("game_updates.json", updates)
    _write("site_updates.json", site)
    _write("pickup_banners.json", banners)
    print(
        f"config={len(cfg)} pickups={len(pickups)} updates={len(updates)} "
        f"site={len(site)} banners={len(banners)}"
    )


if __name__ == "__main__":
    main()
