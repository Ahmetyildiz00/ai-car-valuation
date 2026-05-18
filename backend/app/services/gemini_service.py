"""Gemini-based services.

Currently exposes two things:
    - `get_model()`        — shared, lazily-configured GenerativeModel
    - `analyze_car_images` — computer vision for car listing photos
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache

import google.generativeai as genai
import pillow_avif  # noqa: F401  — registers AVIF support on PIL
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"


@lru_cache(maxsize=1)
def get_model():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()


VISION_PROMPT = """You are an expert automotive appraiser. Analyze these car images (may be multiple angles of the same vehicle) and identify the vehicle and its condition.

Provide:
1. Brand (make): e.g. Renault, Volkswagen, BMW
2. Model: e.g. Clio, Golf, 3 Series
3. Body Type: sedan, hatchback, SUV, coupe, station wagon, etc.
4. Color
5. Exterior Condition (1-10)
6. Paint Quality (1-10)
7. Visible Damages: list of damages (dents, scratches, rust, broken parts) — empty list if none
8. Cleanliness (1-10)
9. Overall Condition Score (1-10)

If any field cannot be determined confidently, use "unknown" for strings or null for numbers.

Return ONLY a valid JSON object. The "notes" field and items in "visible_damages" MUST be in Turkish (Türkçe):
{
    "brand": "<string>",
    "model": "<string>",
    "body_type": "<string>",
    "color": "<string, Türkçe>",
    "exterior_condition": <number>,
    "paint_quality": <number>,
    "visible_damages": ["<Türkçe hasar açıklaması>"],
    "cleanliness": <number>,
    "overall_score": <number>,
    "notes": "<Türkçe kısa özet>"
}"""


def analyze_car_images(image_paths: list[str]) -> dict:
    """Extract identification + visual condition from one or more car photos."""
    imgs = [Image.open(p) for p in image_paths]
    try:
        response = get_model().generate_content([VISION_PROMPT, *imgs])
        return json.loads(_strip_fences(response.text))
    except Exception as e:
        logger.error(f"Gemini image analysis failed: {e}")
        return {
            "brand": "unknown",
            "model": "unknown",
            "body_type": "unknown",
            "color": "unknown",
            "exterior_condition": 5,
            "paint_quality": 5,
            "visible_damages": [],
            "cleanliness": 5,
            "overall_score": 5,
            "notes": "Image analysis unavailable",
        }
