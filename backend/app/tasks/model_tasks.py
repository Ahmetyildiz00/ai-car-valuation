"""Background tasks for ML model lifecycle: training and embedding backfill."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone

from redis import Redis

from app.core.broker import broker
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.valuation import ScrapedCar
from app.services.valuation import embedding, ml_model

logger = logging.getLogger(__name__)

TRAIN_STATUS_KEY = "admin:train_model:status"
EMBED_STATUS_KEY = "admin:backfill_embeddings:status"


def _redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _set(key: str, payload: dict) -> None:
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    _redis().set(key, json.dumps(payload), ex=60 * 60 * 24)


def _get(key: str) -> dict:
    raw = _redis().get(key)
    if not raw:
        return {"state": "idle"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"state": "idle"}


def get_train_status() -> dict:
    return _get(TRAIN_STATUS_KEY)


def clear_train_status() -> None:
    _redis().delete(TRAIN_STATUS_KEY)


def get_embed_status() -> dict:
    return _get(EMBED_STATUS_KEY)


def clear_embed_status() -> None:
    _redis().delete(EMBED_STATUS_KEY)


def _set_status(payload: dict) -> None:
    _set(TRAIN_STATUS_KEY, payload)


@broker.task(task_name="train_model")
async def train_model_task() -> dict:
    _set_status({"state": "running"})
    db = SessionLocal()
    try:
        info = ml_model.train_model(db)
        ml_model.load_model(force=True)  # refresh in-process cache
        result = asdict(info)
        _set_status({"state": "completed", **result})
        return result
    except Exception as e:
        logger.exception("Model training failed")
        _set_status({"state": "error", "error": str(e)})
        raise
    finally:
        db.close()


BATCH_SIZE = 200


@broker.task(task_name="backfill_embeddings")
async def backfill_embeddings_task(force: bool = False) -> dict:
    """Compute embeddings for scraped_cars that don't have one yet.

    If `force=True`, recompute embeddings for ALL rows.
    """
    db = SessionLocal()
    processed = 0
    try:
        if force:
            total = db.query(ScrapedCar).count()
        else:
            total = db.query(ScrapedCar).filter(ScrapedCar.embedding.is_(None)).count()
        _set(EMBED_STATUS_KEY, {"state": "running", "processed": 0, "total": total})

        offset = 0
        while True:
            q = db.query(ScrapedCar).order_by(ScrapedCar.id)
            if not force:
                # in non-force mode, the same filter naturally narrows each pass
                q = q.filter(ScrapedCar.embedding.is_(None))
            else:
                q = q.offset(offset)
            batch = q.limit(BATCH_SIZE).all()
            if not batch:
                break

            vectors = embedding.embed_cars(batch)
            for car, vec in zip(batch, vectors):
                car.embedding = vec
            db.commit()

            processed += len(batch)
            offset += len(batch)
            _set(EMBED_STATUS_KEY, {
                "state": "running", "processed": processed, "total": total,
            })

        _set(EMBED_STATUS_KEY, {
            "state": "completed", "processed": processed, "total": total,
        })
        return {"processed": processed, "total": total}
    except Exception as e:
        logger.exception("Embedding backfill failed")
        _set(EMBED_STATUS_KEY, {"state": "error", "error": str(e), "processed": processed})
        raise
    finally:
        db.close()
