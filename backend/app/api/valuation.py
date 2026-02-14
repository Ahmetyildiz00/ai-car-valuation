import os
import shutil
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.valuation import Valuation
from app.schemas.valuation import ValuationListResponse, ValuationRequest, ValuationResponse
from app.scraper.arabam_scraper import get_market_data
from app.services.gemini_service import analyze_car_image, predict_price

router = APIRouter(prefix="/valuations", tags=["Valuations"])

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "car_valuation_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation(
    data: ValuationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a valuation based on car details (text only, no image)."""
    car_data = data.model_dump()

    # Get market data for comparison
    market_cars = get_market_data(data.brand, data.model, data.year, db)
    market_data = [
        {
            "brand": c.brand,
            "model": c.model,
            "year": c.year,
            "mileage": c.mileage,
            "price": c.price,
        }
        for c in market_cars
    ]

    prediction = predict_price(car_data, image_analysis=None, market_data=market_data)

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
    return valuation


@router.post("/with-image", response_model=ValuationResponse, status_code=status.HTTP_201_CREATED)
async def create_valuation_with_image(
    brand: str,
    model: str,
    year: int,
    mileage: int,
    fuel_type: str,
    transmission: str,
    body_type: str | None = None,
    color: str | None = None,
    engine_size: str | None = None,
    damage_records: str | None = None,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a valuation with both text data and an uploaded car image."""
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image",
        )

    # Save uploaded image
    ext = image.filename.split(".")[-1] if image.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(image.file, f)

    try:
        # Analyze image with Gemini
        image_analysis = analyze_car_image(filepath)

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
            {
                "brand": c.brand,
                "model": c.model,
                "year": c.year,
                "mileage": c.mileage,
                "price": c.price,
            }
            for c in market_cars
        ]

        prediction = predict_price(car_data, image_analysis, market_data)

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
            image_url=filename,
        )
        db.add(valuation)
        db.commit()
        db.refresh(valuation)
        return valuation
    finally:
        # Clean up temp file
        if os.path.exists(filepath):
            os.remove(filepath)


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
