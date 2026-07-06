from __future__ import annotations

import base64
import os

from openai import OpenAI

from .models import CharacterSnapshot, EchoItem, VisionExtractionResult
from .parser import extract_json_object, normalize_extraction

SYSTEM_PROMPT = """You extract Wuthering Waves account/build screenshots into strict JSON.
Return only JSON matching the requested schema. If a value is unclear, set it to null and add the field path to uncertain_fields.
"""


def _mock_extraction() -> VisionExtractionResult:
    return VisionExtractionResult(
        screen_type="character_status",
        snapshot=CharacterSnapshot(character_name="Changli", character_level=90, role="main_dps", echoes=[EchoItem(slot=str(index)) for index in range(1, 6)]),
        warnings=["Mock extraction returned because OPENAI_API_KEY is not configured."],
        confidence=0.0,
    )


def extract_from_image(image_bytes: bytes, filename: str | None = None) -> VisionExtractionResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _mock_extraction()

    client = OpenAI(api_key=api_key)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Extract this Wuthering Waves screenshot into JSON for build analysis."},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{encoded}"},
                ],
            },
        ],
    )
    text = response.output_text
    parsed = extract_json_object(text)
    return normalize_extraction(parsed, raw_output=text)