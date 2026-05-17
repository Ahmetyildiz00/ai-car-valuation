"""Price prediction ML model.

Approach:
    - Target is `log1p(price)` to make the heavy-tailed price distribution
      tractable for tree regressors. Predictions are reversed with `expm1`.
    - Per-(brand, model) outlier filter via ±3σ on log-price before training.
    - HistGradientBoostingRegressor — native NaN handling, fast, accurate.
    - Categorical features one-hot encoded (with rare-category bucketing).
    - `engine_power` parsed from arabam.com strings ("90 hp", "101 - 125 HP")
      into a single numeric mean.

Two model locations:
    - /app/models_bundled/  — committed in repo, image-resident
    - /app/models/          — volume, prod re-train output

Volume wins if both exist.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy.orm import Session

from app.models.valuation import ScrapedCar

logger = logging.getLogger(__name__)

NUMERIC_FEATURES = ["year", "mileage", "engine_power_hp", "engine_size_l"]
CATEGORICAL_FEATURES = ["brand", "model", "fuel_type", "transmission", "body_type"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

BUNDLED_DIR = Path("/app/models_bundled")
VOLUME_DIR = Path("/app/models")
MODEL_FILE = "price_model.pkl"
META_FILE = "price_model.meta.json"

MIN_TRAINING_SAMPLES = 200
OUTLIER_SIGMA = 3.0
MIN_GROUP_FOR_OUTLIER = 6


@dataclass
class ModelInfo:
    trained_at: str
    n_samples: int
    n_train: int
    n_test: int
    mae: float
    r2: float
    source: str  # "volume" or "bundled"


_HP_RE = re.compile(r"(\d+)")
_NUM_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def _parse_engine_power(raw: str | None) -> float | None:
    """Parse arabam.com power strings into a single HP number.

    Examples:
        '90 hp'        -> 90
        '101 - 125 HP' -> 113   (mean of range)
    """
    if not raw:
        return None
    nums = [int(m) for m in _HP_RE.findall(raw)]
    if not nums:
        return None
    return float(sum(nums) / len(nums))


def _parse_engine_size(raw: str | None) -> float | None:
    """Parse engine displacement strings into liters.

    Accepts both user input ("1.6", "2.0 L") and arabam.com format ("1598 cc",
    "1.6 cm3", "1600 cm3 - 1800 cm3"). Returns liters (e.g. 1.6).
    """
    if not raw:
        return None
    nums = [float(m.replace(",", ".")) for m in _NUM_RE.findall(raw)]
    if not nums:
        return None
    avg = sum(nums) / len(nums)
    # Heuristic: if value > 100, it's in cc; otherwise it's already liters.
    return avg / 1000 if avg > 100 else avg


def _rows_to_dataframe(rows: list[ScrapedCar]) -> tuple[pd.DataFrame, np.ndarray]:
    records: list[dict[str, Any]] = []
    prices: list[float] = []
    for r in rows:
        if not (r.year and r.mileage and r.price and r.price > 0 and r.brand and r.model):
            continue
        records.append({
            "year": int(r.year),
            "mileage": int(r.mileage),
            "engine_power_hp": _parse_engine_power(r.engine_power),
            "engine_size_l": _parse_engine_size(r.engine_size),
            "brand": r.brand,
            "model": r.model,
            "fuel_type": (r.fuel_type or "unknown").lower(),
            "transmission": (r.transmission or "unknown").lower(),
            "body_type": (r.body_type or "unknown").lower(),
        })
        prices.append(float(r.price))
    df = pd.DataFrame(records, columns=ALL_FEATURES)
    return df, np.array(prices)


def _filter_outliers(df: pd.DataFrame, prices: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    """Drop rows whose log-price is >OUTLIER_SIGMA away from their (brand,model) group mean."""
    log_p = np.log1p(prices)
    keep = np.ones(len(prices), dtype=bool)

    grouped = df.groupby(["brand", "model"], sort=False).indices
    for _, idx_arr in grouped.items():
        if len(idx_arr) < MIN_GROUP_FOR_OUTLIER:
            continue
        group_log = log_p[idx_arr]
        mu = group_log.mean()
        sigma = group_log.std() or 1.0
        outlier_mask = np.abs(group_log - mu) > OUTLIER_SIGMA * sigma
        keep[idx_arr[outlier_mask]] = False

    dropped = (~keep).sum()
    if dropped:
        logger.info(f"Outlier filter removed {dropped} rows ({dropped / len(prices):.1%})")
    return df.loc[keep].reset_index(drop=True), prices[keep]


def _build_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", min_frequency=3, sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="passthrough",
    )
    return Pipeline([
        ("pre", pre),
        ("hgb", HistGradientBoostingRegressor(
            max_iter=500,
            learning_rate=0.05,
            max_leaf_nodes=63,
            min_samples_leaf=15,
            l2_regularization=0.1,
            random_state=42,
        )),
    ])


def train_model(db: Session, *, output_dir: Path = VOLUME_DIR) -> ModelInfo:
    """Train HGB on current scraped_cars; persist to `output_dir`."""
    rows = db.query(ScrapedCar).all()
    df, prices = _rows_to_dataframe(rows)

    if len(df) < MIN_TRAINING_SAMPLES:
        raise ValueError(
            f"Not enough samples to train ({len(df)} < {MIN_TRAINING_SAMPLES})"
        )

    df, prices = _filter_outliers(df, prices)
    y_log = np.log1p(prices)

    X_train, X_test, y_train_log, y_test_log = train_test_split(
        df, y_log, test_size=0.15, random_state=42
    )

    pipe = _build_pipeline()
    pipe.fit(X_train, y_train_log)

    y_pred_log = pipe.predict(X_test)
    y_pred = np.expm1(y_pred_log)
    y_test = np.expm1(y_test_log)

    mae = float(mean_absolute_error(y_test, y_pred))
    r2 = float(r2_score(y_test, y_pred))

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, output_dir / MODEL_FILE)

    info = ModelInfo(
        trained_at=datetime.now(timezone.utc).isoformat(),
        n_samples=len(df),
        n_train=len(X_train),
        n_test=len(X_test),
        mae=mae,
        r2=r2,
        source="volume" if output_dir == VOLUME_DIR else "bundled",
    )
    (output_dir / META_FILE).write_text(json.dumps(asdict(info), indent=2))
    logger.info(f"Trained model: n={info.n_samples} mae={mae:.0f} r2={r2:.3f}")
    return info


_cached_pipeline: tuple[Pipeline, ModelInfo] | None = None


def _resolve_dir() -> Path | None:
    for d in (VOLUME_DIR, BUNDLED_DIR):
        if (d / MODEL_FILE).exists():
            return d
    return None


def load_model(force: bool = False) -> tuple[Pipeline, ModelInfo] | None:
    """Load model from volume (preferred) or bundled fallback."""
    global _cached_pipeline
    if _cached_pipeline is not None and not force:
        return _cached_pipeline
    d = _resolve_dir()
    if d is None:
        return None
    pipe: Pipeline = joblib.load(d / MODEL_FILE)
    meta_path = d / META_FILE
    if meta_path.exists():
        meta_dict = json.loads(meta_path.read_text())
    else:
        meta_dict = {
            "trained_at": "unknown", "n_samples": 0, "n_train": 0,
            "n_test": 0, "mae": 0.0, "r2": 0.0, "source": d.name,
        }
    info = ModelInfo(**meta_dict)
    info.source = "volume" if d == VOLUME_DIR else "bundled"
    _cached_pipeline = (pipe, info)
    return _cached_pipeline


def predict_price(features: dict[str, Any]) -> float | None:
    loaded = load_model()
    if loaded is None:
        return None
    pipe, _ = loaded
    row = {
        "year": features.get("year"),
        "mileage": features.get("mileage"),
        "engine_power_hp": _parse_engine_power(features.get("engine_power")),
        "engine_size_l": _parse_engine_size(features.get("engine_size")),
        "brand": features.get("brand") or "unknown",
        "model": features.get("model") or "unknown",
        "fuel_type": (features.get("fuel_type") or "unknown").lower(),
        "transmission": (features.get("transmission") or "unknown").lower(),
        "body_type": (features.get("body_type") or "unknown").lower(),
    }
    df = pd.DataFrame([row], columns=ALL_FEATURES)
    pred_log = pipe.predict(df)
    return float(np.expm1(pred_log[0]))


def model_info() -> ModelInfo | None:
    loaded = load_model()
    if loaded is None:
        return None
    return loaded[1]
