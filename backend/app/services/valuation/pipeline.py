"""Top-level orchestration of the valuation engine.

Flow:
    1. Retrieve comparable listings (SQL → semantic fallback if sparse)
    2. Statistical baseline from comparables (median or mileage-adjusted linear)
    3. ML model prediction (if a trained model is available)
    4. Blend: weighted average of ML + stats, adjusted by image condition
    5. LLM narrative (Gemini) for the user-facing explanation

The function returns a `ValuationResult` whose price/min/max/score are
fully numeric — never produced by an LLM.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.services.valuation.baseline import statistical_baseline
from app.services.valuation.embedding import find_semantic_neighbors
from app.services.valuation.llm import explain_price
from app.services.valuation.ml_model import predict_price as ml_predict
from app.services.valuation.retrieval import MIN_SAMPLES, find_comparable_cars
from app.services.valuation.schemas import CarFeatures, ValuationResult

logger = logging.getLogger(__name__)

# Weight given to the ML prediction when both ML and stats baseline exist.
ML_WEIGHT = 0.6

# How much the visual condition score (1-10) can move the final price.
# A score of 5 is neutral; 10 → +CONDITION_SWING, 1 → -CONDITION_SWING.
CONDITION_SWING = 0.10  # ±10%


def _condition_multiplier(image_analysis: dict | None) -> float:
    if not image_analysis:
        return 1.0
    score = image_analysis.get("overall_score")
    if not isinstance(score, (int, float)):
        return 1.0
    # map 1..10 → -1..+1, then scale
    centered = (float(score) - 5.0) / 5.0
    return 1.0 + CONDITION_SWING * centered


def predict_valuation(db: Session, features: CarFeatures) -> ValuationResult:
    sources: dict = {}

    # 1) retrieval
    retrieval = find_comparable_cars(db, features)
    cars = retrieval.cars
    sources["retrieval_strategy"] = retrieval.strategy
    sources["n_comparable"] = len(cars)

    # 2) sparse fallback via embeddings
    if len(cars) < MIN_SAMPLES:
        try:
            extra = find_semantic_neighbors(db, features.text_repr(), k=30)
            # dedupe by id
            seen = {c.id for c in cars}
            cars = list(cars) + [c for c in extra if c.id not in seen]
            sources["semantic_fallback"] = len(extra)
        except Exception as e:
            logger.warning(f"Semantic fallback failed: {e}")
            sources["semantic_fallback_error"] = str(e)

    # 3) statistical baseline
    baseline = statistical_baseline(cars, features.mileage)
    if baseline:
        sources["baseline_method"] = baseline.method
        sources["baseline_price"] = round(baseline.price)

    # 4) ML prediction
    ml_features = {
        "year": features.year,
        "mileage": features.mileage,
        "engine_power": None,  # not collected from end users yet
        "brand": features.brand,
        "model": features.model,
        "fuel_type": features.fuel_type,
        "transmission": features.transmission,
        "body_type": features.body_type,
    }
    ml_price = None
    try:
        ml_price = ml_predict(ml_features)
    except Exception as e:
        logger.warning(f"ML prediction failed: {e}")
    sources["ml_price"] = round(ml_price) if ml_price else None

    # 5) blend
    if ml_price and baseline:
        blended = ML_WEIGHT * ml_price + (1 - ML_WEIGHT) * baseline.price
        price_min = baseline.price_min
        price_max = baseline.price_max
    elif baseline:
        blended = baseline.price
        price_min = baseline.price_min
        price_max = baseline.price_max
    elif ml_price:
        blended = ml_price
        price_min = ml_price * 0.85
        price_max = ml_price * 1.15
    else:
        # No data at all — degraded mode
        blended = 0.0
        price_min = 0.0
        price_max = 0.0

    # 6) condition adjustment
    mult = _condition_multiplier(features.image_analysis)
    final_price = blended * mult
    price_min *= mult
    price_max *= mult
    sources["condition_multiplier"] = round(mult, 3)

    # 7) condition score (passes through from image analysis if present)
    condition_score = 5.0
    if features.image_analysis:
        score = features.image_analysis.get("overall_score")
        if isinstance(score, (int, float)):
            condition_score = float(score)

    # 8) narrative
    if final_price > 0:
        analysis = explain_price(features, final_price, cars, sources)
    else:
        analysis = (
            "Yeterli karşılaştırılabilir ilan bulunamadığı için fiyat tahmini "
            "şu an üretilemiyor. Daha fazla araç verisi toplandıkça tahmin doğruluğu artacaktır."
        )

    return ValuationResult(
        predicted_price=round(final_price),
        price_min=round(price_min),
        price_max=round(price_max),
        condition_score=condition_score,
        analysis=analysis,
        sources=sources,
    )
