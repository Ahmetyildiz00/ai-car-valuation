import json
import logging

import google.generativeai as genai
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)


def _configure_gemini():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel("gemini-2.5-flash")


def analyze_car_images(image_paths: list[str]) -> dict:
    """Analyze one or more car images to extract identification + visual condition."""
    model = _configure_gemini()
    imgs = [Image.open(p) for p in image_paths]

    prompt = """You are an expert automotive appraiser. Analyze these car images (may be multiple angles of the same vehicle) and identify the vehicle and its condition.

Provide:
1. **Brand** (make): e.g. Renault, Volkswagen, BMW
2. **Model**: e.g. Clio, Golf, 3 Series
3. **Body Type**: sedan, hatchback, SUV, coupe, station wagon, etc.
4. **Color**
5. **Exterior Condition** (1-10)
6. **Paint Quality** (1-10)
7. **Visible Damages**: list of damages (dents, scratches, rust, broken parts) — empty list if none
8. **Cleanliness** (1-10)
9. **Overall Condition Score** (1-10)

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

    try:
        response = model.generate_content([prompt, *imgs])
        text = response.text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return json.loads(text)
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


def analyze_car_image(image_path: str) -> dict:
    """Backwards-compatible single-image wrapper."""
    return analyze_car_images([image_path])


def predict_price(
    car_data: dict,
    image_analysis: dict | None = None,
    market_data: list[dict] | None = None,
) -> dict:
    """Use Gemini to predict the car price based on all available data."""
    model = _configure_gemini()

    market_context = ""
    if market_data:
        market_context = "\n\n**Similar Cars on Market (from arabam.com):**\n"
        for car in market_data[:10]:
            market_context += (
                f"- {car.get('brand', '')} {car.get('model', '')} "
                f"({car.get('year', '')}) - {car.get('mileage', '')} km - "
                f"₺{car.get('price', 'N/A'):,.0f}\n"
            )

    image_context = ""
    if image_analysis:
        image_context = f"""

**Visual Condition Analysis (from uploaded image):**
- Exterior Condition: {image_analysis.get('exterior_condition', 'N/A')}/10
- Paint Quality: {image_analysis.get('paint_quality', 'N/A')}/10
- Visible Damages: {', '.join(image_analysis.get('visible_damages', [])) or 'None detected'}
- Cleanliness: {image_analysis.get('cleanliness', 'N/A')}/10
- Overall Visual Score: {image_analysis.get('overall_score', 'N/A')}/10
- Notes: {image_analysis.get('notes', '')}"""

    prompt = f"""You are an expert used car appraiser specializing in the Turkish automotive market.
Based on all provided data, estimate the market price of this vehicle.

**Car Details:**
- Brand: {car_data.get('brand', 'Unknown')}
- Model: {car_data.get('model', 'Unknown')}
- Year: {car_data.get('year', 'Unknown')}
- Mileage: {car_data.get('mileage', 'Unknown')} km
- Fuel Type: {car_data.get('fuel_type', 'Unknown')}
- Transmission: {car_data.get('transmission', 'Unknown')}
- Body Type: {car_data.get('body_type', 'Unknown')}
- Color: {car_data.get('color', 'Unknown')}
- Engine Size: {car_data.get('engine_size', 'Unknown')}
- Reported Damages: {car_data.get('damage_records', 'None reported')}
{image_context}
{market_context}

Analyze all the data and provide your price prediction. Consider:
1. The car's age and mileage depreciation
2. Brand value and model popularity in Turkey
3. Fuel type preference in Turkish market
4. Visual condition (if image data available)
5. Current market prices for similar vehicles
6. Damage history impact on value

Return ONLY a valid JSON object. The "analysis" field MUST be written in Turkish (Türkçe):
{{
    "predicted_price": <number in TL>,
    "price_min": <number in TL>,
    "price_max": <number in TL>,
    "condition_score": <1-10>,
    "confidence": "<low/medium/high>",
    "analysis": "<Türkçe, 3-5 cümlelik detaylı değerlendirme: fiyatın dayanakları, dikkate alınan faktörler ve fiyat gerekçesi>"
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        result = json.loads(text)
        return {
            "predicted_price": float(result.get("predicted_price", 0)),
            "price_min": float(result.get("price_min", 0)),
            "price_max": float(result.get("price_max", 0)),
            "condition_score": float(result.get("condition_score", 5)),
            "analysis": result.get("analysis", ""),
        }
    except Exception as e:
        logger.error(f"Gemini price prediction failed: {e}")
        return {
            "predicted_price": 0,
            "price_min": 0,
            "price_max": 0,
            "condition_score": 5,
            "analysis": "Price prediction is currently unavailable. Please try again later.",
        }
