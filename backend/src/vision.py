from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from openai import OpenAI

from .models import VisionExtractionResult
from .parser import extract_json_object, normalize_extraction

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_EXTRACTION_PATH = DATA_DIR / "sample_extraction.json"

VISION_PROMPT = """You are analyzing screenshots from Wuthering Waves.
Extract only visible information.
Do not guess missing fields.
Return strict JSON matching the schema.
If a value is unclear, set it to null and add the field path to uncertain_fields.
Preserve raw visible text in raw_text."""


def _load_mock_result() -> VisionExtractionResult:
    with SAMPLE_EXTRACTION_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    result = normalize_extraction(data)
    if not any("mock" in warning.lower() for warning in result.warnings):
        result.warnings.append("Mock extraction mode: OPENAI_API_KEY is not configured.")
    return result


def extract_from_image(image_bytes: bytes, filename: str | None = None) -> VisionExtractionResult:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _load_mock_result()

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    client = OpenAI(api_key=api_key)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": VISION_PROMPT},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_b64}"},
                    ],
                }
            ],
        )
        raw_output = response.output_text
        data = extract_json_object(raw_output)
        return normalize_extraction(data, raw_output=raw_output)
    except Exception as exc:
        return VisionExtractionResult(
            warnings=[f"Vision extraction failed: {exc}"],
            raw_model_output=str(exc),
        )
