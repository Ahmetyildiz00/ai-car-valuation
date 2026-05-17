"""Generate a Turkish natural-language explanation of an already-computed price.

The model is NOT allowed to invent a price — we pass the final number in
and ask only for justification. Falls back to a deterministic template
if the Gemini call fails (so the user never sees a missing analysis).
"""
from __future__ import annotations

import logging
from typing import Sequence

from app.models.valuation import ScrapedCar
from app.services.gemini_service import get_model
from app.services.valuation.schemas import CarFeatures

logger = logging.getLogger(__name__)


def _template_explanation(
    car: CarFeatures, price: float, n_comparable: int
) -> str:
    fmt = f"{price:,.0f}".replace(",", ".")
    age = max(0, 2026 - car.year)
    parts = [
        f"{car.brand} {car.model} ({car.year}), {car.mileage:,} km".replace(",", "."),
        f"benzer {n_comparable} ilanın istatistiksel analizi sonucu yaklaşık {fmt} TL değerinde tahmin edildi.",
    ]
    if age > 8:
        parts.append(f"Aracın {age} yaşında olması fiyatı belirgin şekilde aşağı çekmektedir.")
    if car.damage_records:
        parts.append(f"Bildirilen hasar/değişen parça bilgisi (\"{car.damage_records}\") değerlemeye dahil edilmiştir.")
    return " ".join(parts)


def explain_price(
    car: CarFeatures,
    price: float,
    comparables: Sequence[ScrapedCar],
    sources: dict,
) -> str:
    """Ask Gemini for a 3-5 sentence Turkish explanation of the given price."""
    market_lines: list[str] = []
    for c in comparables[:5]:
        market_lines.append(
            f"- {c.brand} {c.model} ({c.year}) — {c.mileage:,} km — {c.price:,.0f} TL".replace(",", ".")
        )
    market_block = "\n".join(market_lines) if market_lines else "(benzer ilan bulunamadı)"

    image_block = ""
    if car.image_analysis:
        ia = car.image_analysis
        image_block = (
            "Görsel analiz: "
            f"durum {ia.get('overall_score', '?')}/10, "
            f"boya {ia.get('paint_quality', '?')}/10, "
            f"hasar: {', '.join(ia.get('visible_damages', [])) or 'tespit edilmedi'}."
        )

    sources_summary = ", ".join(f"{k}={v}" for k, v in sources.items() if v is not None)

    prompt = f"""Aşağıdaki araç için tahmini piyasa değeri **{price:,.0f} TL** olarak hesaplandı.
Bu fiyatı kullanıcıya 3-5 cümlelik Türkçe bir paragrafla açıkla. SADECE açıklama metni döndür — JSON, başlık veya farklı format YOK.

Araç:
- {car.brand} {car.model} ({car.year})
- {car.mileage:,} km, {car.fuel_type or '?'}, {car.transmission or '?'}
- Hasar/değişen: {car.damage_records or 'belirtilmedi'}
{image_block}

Benzer piyasa ilanları:
{market_block}

Tahmin yöntemleri: {sources_summary}

Açıklamada şunlara değin:
1. Yıl ve kilometrenin fiyata etkisi
2. Hasar/durum varsa onun etkisi
3. Piyasadaki benzer ilanlarla kıyaslama
""".replace(",", ".")

    try:
        response = get_model().generate_content(prompt)
        text = (response.text or "").strip()
        if not text:
            raise ValueError("empty response")
        return text
    except Exception as e:
        logger.warning(f"Gemini narrative failed, using template: {e}")
        return _template_explanation(car, price, len(comparables))
