"""Sentence-transformer embeddings for semantic car-listing similarity.

A single 384-dim MiniLM model is loaded lazily on first use and kept
in memory for the lifetime of the process.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.valuation import ScrapedCar

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer  # heavy import
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)


def _car_text(car: ScrapedCar) -> str:
    parts = [car.brand or "", car.model or "", str(car.year or "")]
    for v in (car.fuel_type, car.transmission, car.body_type, car.color):
        if v:
            parts.append(v)
    parts.append(f"{car.mileage or 0}km")
    return " ".join(p for p in parts if p)


def embed_text(text: str) -> list[float]:
    return _model().encode(text, normalize_embeddings=True).tolist()


def embed_cars(cars: Iterable[ScrapedCar]) -> list[list[float]]:
    texts = [_car_text(c) for c in cars]
    if not texts:
        return []
    arr = _model().encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    return arr.tolist()


def find_semantic_neighbors(
    db: Session, query_text: str, k: int = 20
) -> list[ScrapedCar]:
    """Return up to `k` cars whose embedding is closest to `query_text`.

    Cars without embeddings are silently skipped (NULL ordering).
    """
    vec = embed_text(query_text)
    return (
        db.query(ScrapedCar)
        .filter(ScrapedCar.embedding.is_not(None))
        .order_by(ScrapedCar.embedding.l2_distance(vec))
        .limit(k)
        .all()
    )
