"""표시용 소형 순수 헬퍼 — 무기 커브값·에코 옵션 조회.

캐릭/멤버 최종 스탯은 여기서 계산 안 함 → engine.member_preview(권위 엔진) 사용.
여기 있는 건 엔진을 안 거치는 단순 표(무기 곡선, game_config 에코 옵션)뿐.
"""
from __future__ import annotations


def curve_value(points: list[dict], level: int) -> float:
    """무기 속성 곡선에서 레벨값. 동일 레벨 중복(승급 구간)은 마지막(승급 후) 채택."""
    best = None
    for p in points:
        if p.get("level") == level:
            best = p.get("value")
    if best is not None:
        return best
    return min(points, key=lambda p: abs(p.get("level", 0) - level)).get("value", 0) if points else 0


def echo_main_options(game_config: dict, cost: int) -> list[dict]:
    """코스트별 메인옵션 후보 [{key,max}]."""
    return (game_config.get("echo_stats", {}).get("main", {}) or {}).get(str(cost), [])


def echo_sub_defs(game_config: dict) -> list[dict]:
    """서브옵션 정의 [{key,min,max}]."""
    return game_config.get("echo_stats", {}).get("sub", [])


def echo_sub_slots(game_config: dict, grade: int) -> int:
    """등급(1~5)당 서브옵션 슬롯 수."""
    return (game_config.get("echo_stats", {}).get("subSlots", {}) or {}).get(str(grade), 0)


if __name__ == "__main__":  # smoke: curve pick + config lookups
    import sys

    sys.path.insert(0, r"C:\Users\JungSu\Desktop\wawa-ai-coach\backend")
    from native import engine

    w = engine.weapons()[0]
    pts = w["properties"][0]["curve"]
    assert curve_value(pts, 1) == pts[0]["value"]
    assert curve_value(pts, 90) > 0
    gc = engine.game_config()
    assert echo_main_options(gc, 4), "cost-4 main options empty"
    assert echo_sub_defs(gc), "sub defs empty"
    assert echo_sub_slots(gc, 5) == 5
    print("calc ok")
