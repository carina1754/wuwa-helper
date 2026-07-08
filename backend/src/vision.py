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
        warnings=["Mock extraction returned because LLM_BASE_URL is not configured."],
        confidence=0.0,
    )


def extract_from_image(image_bytes: bytes, filename: str | None = None) -> VisionExtractionResult:
    # Local OpenAI-compatible multimodal LLM (llama.cpp llama-server, Chat Completions API).
    base_url = os.getenv("LLM_BASE_URL")
    if not base_url:
        return _mock_extraction()

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "sk-local"))
    encoded = base64.b64encode(image_bytes).decode("ascii")
    model = os.getenv("LLM_MODEL", "wuwa-vlm")
    response = client.chat.completions.create(
        model=model,
        temperature=0.1,  # extraction should be deterministic
        response_format={"type": "json_object"},  # llama-server enforces valid JSON
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract this Wuthering Waves screenshot into JSON for build analysis."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            },
        ],
    )
    text = response.choices[0].message.content or ""
    parsed = extract_json_object(text)
    return normalize_extraction(parsed, raw_output=text)