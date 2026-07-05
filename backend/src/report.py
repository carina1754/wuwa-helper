from __future__ import annotations

from .models import CharacterSnapshot, Diagnosis


def generate_report(snapshot: CharacterSnapshot, diagnoses: list[Diagnosis]) -> str:
    sorted_items = sorted(diagnoses, key=lambda item: item.score)
    biggest_problems = sorted_items[:3]
    actions: list[str] = []
    for diagnosis in biggest_problems:
        actions.extend(diagnosis.recommended_actions[:1])
    actions = actions[:3] or ["Enter more character and echo data, then run diagnosis again."]
    character = snapshot.character_name or "Current character"
    lines = [
        "요약",
        f"{character}의 현재 빌드는 에코와 핵심 스탯을 우선 점검해야 합니다.",
        "",
        "현재 상태",
        f"진단 항목 {len(diagnoses)}개를 평가했습니다.",
        "",
        "가장 큰 문제 3개",
    ]
    lines.extend(f"- {item.target_name or item.target_type}: {item.grade} ({item.score})" for item in biggest_problems)
    lines.extend(["", "바로 할 일 3개"])
    lines.extend(f"- {action}" for action in actions)
    lines.extend(["", "보류해도 되는 것", "- 완벽한 부옵션 파밍은 기본 세트와 주옵션을 맞춘 뒤 진행하세요."])
    lines.extend(["", "장기 목표", "- 역할에 맞는 무기, 세트, 치명/공격/에너지 균형을 안정화하세요."])
    lines.extend(["", "주의사항", "- 이 결과는 비공식 팬 도구의 추정이며 게임 내 실제 성능과 다를 수 있습니다."])
    return "\n".join(lines)
