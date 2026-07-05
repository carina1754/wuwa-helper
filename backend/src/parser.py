from __future__ import annotations

import json
from typing import Any

from .models import EchoItem, VisionExtractionResult


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def normalize_extraction(data: dict[str, Any], raw_output: str | None = None) -> VisionExtractionResult:
    result = VisionExtractionResult.model_validate(data)
    echoes = list(result.snapshot.echoes)
    while len(echoes) < 5:
        echoes.append(EchoItem(slot=str(len(echoes) + 1)))
    result.snapshot.echoes = echoes[:5]
    if raw_output is not None:
        result.raw_model_output = raw_output
    return result
