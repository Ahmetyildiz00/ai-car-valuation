import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.models.valuation import Valuation
from app.schemas.valuation import ValuationListResponse, ValuationRequest, ValuationResponse
from app.scraper.arabam_scraper import get_market_data
from app.services.anon_quota import consume as consume_anon_quota, get_remaining as get_anon_remaining
from app.services.gemini_service import analyze_car_images, predict_price
from app.services.subscription_service import (
    TIER_LIMITS,
    get_or_create_subscription,
    get_remaining as get_sub_remaining,
    get_usage_count,
    has_quota,
    increment_usage,
)

router = APIRouter(prefix="/valuations", tags=["Valuations"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "car_valuation_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _anon_quota_error():
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Ücretsiz deneme hakkınız doldu. Sınırsız değerleme için üye olun.",
            "code": "anonymous_quota_exhausted",
        },
    )


def _sub_quota_error():
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={
            "message": "Aylık değerleme hakkınız doldu. Sınırsız kullanım için Pro aboneliğine geçin.",
            "code": "subscription_quota_exhausted",
        },
    )


def _build_anon_response(car_data: dict, prediction: dict, image_url: str | None) -> ValuationResponse:
    return ValuationResponse(
        id=uuid.uuid4(),
        brand=car_data["brand"],
        model=car_data["model"],
        year=car_data["year"],
        mileage=car_data["mileage"],
        fuel_type=car_data["fuel_type"],
        transmission=car_data["transmission"],
        body_type=car_data.get("body_type"),
        color=car_data.get("color"),
        engine_size=car_data.get("engine_size"),
        damage_records=car_data.get("damage_records"),
        predicted_price=prediction["predicted_price"],
        price_min=prediction["price_min"],
        price_max=prediction["price_max"],
        condition_score=prediction["condition_score"],
        ai_analysis=prediction["analysis"],
        image_url=image_url,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/quota")
def get_quota(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Unified quota endpoint: anonymous or authenticated status."""
    if not current_user:
        return {
            "authenticated": False,
            "tier": "anonymous",
            "remaining": get_anon_remaining(request),
            "limit": None,
            "used": None,
            "unlimited": False,
        }
    sub = get_or_create_subscription(current_user, db)
    limit = TIER_LIMITS.get(sub.tier)
    used = get_usage_count(current_user.id, db)
    remaining = get_sub_remaining(current_user, db)
    return {
        "authenticated": True,
        "tier": sub.tier,
        "remaining": remaining,
        "limit": limit,
        "used": used,
        "unlimited": limit is None,
    }


@router.post("/", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation(
    data: ValuationRequest,
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Create a valuation based on car details (text only, no image)."""
    if current_user:
        if not has_quota(current_user, db):
            raise _sub_quota_error()
    else:
        if get_anon_remaining(request) <= 0:
            raise _anon_quota_error()

    car_data = data.model_dump()
    market_cars = get_market_data(data.brand, data.model, data.year, db)
    market_data = [
        {"brand": c.brand, "model": c.model, "year": c.year, "mileage": c.mileage, "price": c.price}
        for c in market_cars
    ]

    prediction = predict_price(car_data, image_analysis=None, market_data=market_data)

    if not current_user:
        consume_anon_quota(request)
        return _build_anon_response(car_data, prediction, None)

    valuation = Valuation(
        user_id=current_user.id,
        brand=data.brand,
        model=data.model,
        year=data.year,
        mileage=data.mileage,
        fuel_type=data.fuel_type,
        transmission=data.transmission,
        body_type=data.body_type,
        color=data.color,
        engine_size=data.engine_size,
        damage_records=data.damage_records,
        predicted_price=prediction["predicted_price"],
        price_min=prediction["price_min"],
        price_max=prediction["price_max"],
        condition_score=prediction["condition_score"],
        ai_analysis=prediction["analysis"],
    )
    db.add(valuation)
    db.commit()
    db.refresh(valuation)
    increment_usage(current_user, db)
    return valuation


def _save_upload(upload: UploadFile) -> str:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )
    ext = upload.filename.split(".")[-1] if upload.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return filepath


def _download_image_url(url: str) -> str:
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL does not point to an image",
                )
            ext = content_type.split("/")[-1].split(";")[0] or "jpg"
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return filepath
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch image from URL: {e}",
        )


@router.post("/with-image", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation_with_image(
    request: Request,
    year: int = Form(...),
    mileage: int = Form(...),
    fuel_type: str = Form(...),
    transmission: str = Form(...),
    engine_size: str | None = Form(None),
    damage_records: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
    image_url: str | None = Form(None),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Create a valuation from one or more car images. Brand/model/color/body_type are inferred by AI."""
    if current_user:
        if not has_quota(current_user, db):
            raise _sub_quota_error()
    else:
        if get_anon_remaining(request) <= 0:
            raise _anon_quota_error()

    if not images and not image_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image or image_url is required",
        )

    saved_paths: list[str] = []
    try:
        if images:
            for img in images[:5]:
                saved_paths.append(_save_upload(img))
        if image_url:
            saved_paths.append(_download_image_url(image_url))

        image_analysis = analyze_car_images(saved_paths)

        brand = image_analysis.get("brand") or "Unknown"
        model = image_analysis.get("model") or "Unknown"
        body_type = image_analysis.get("body_type")
        color = image_analysis.get("color")

        car_data = {
            "brand": brand,
            "model": model,
            "year": year,
            "mileage": mileage,
            "fuel_type": fuel_type,
            "transmission": transmission,
            "body_type": body_type,
            "color": color,
            "engine_size": engine_size,
            "damage_records": damage_records,
        }

        market_cars = get_market_data(brand, model, year, db)
        market_data = [
            {"brand": c.brand, "model": c.model, "year": c.year, "mileage": c.mileage, "price": c.price}
            for c in market_cars
        ]

        prediction = predict_price(car_data, image_analysis, market_data)

        if not current_user:
            consume_anon_quota(request)
            return _build_anon_response(car_data, prediction, None)

        stored_filename = os.path.basename(saved_paths[0]) if saved_paths else None

        valuation = Valuation(
            user_id=current_user.id,
            brand=brand,
            model=model,
            year=year,
            mileage=mileage,
            fuel_type=fuel_type,
            transmission=transmission,
            body_type=body_type,
            color=color,
            engine_size=engine_size,
            damage_records=damage_records,
            predicted_price=prediction["predicted_price"],
            price_min=prediction["price_min"],
            price_max=prediction["price_max"],
            condition_score=prediction["condition_score"],
            ai_analysis=prediction["analysis"],
            image_url=stored_filename,
        )
        db.add(valuation)
        db.commit()
        db.refresh(valuation)
        increment_usage(current_user, db)
        return valuation
    finally:
        for path in saved_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


@router.get("/", response_model=ValuationListResponse)
def list_valuations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all valuations for the current user."""
    valuations = (
        db.query(Valuation)
        .filter(Valuation.user_id == current_user.id)
        .order_by(Valuation.created_at.desc())
        .all()
    )
    return ValuationListResponse(valuations=valuations, total=len(valuations))


@router.get("/{valuation_id}", response_model=ValuationResponse)
def get_valuation(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific valuation."""
    valuation = (
        db.query(Valuation)
        .filter(Valuation.id == valuation_id, Valuation.user_id == current_user.id)
        .first()
    )
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Valuation not found"
        )
    return valuation


@router.delete("/{valuation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_valuation(
    valuation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a valuation."""
    valuation = (
        db.query(Valuation)
        .filter(Valuation.id == valuation_id, Valuation.user_id == current_user.id)
        .first()
    )
    if not valuation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Valuation not found"
        )
    db.delete(valuation)
    db.commit()
