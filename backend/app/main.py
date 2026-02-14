from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.scraper import router as scraper_router
from app.api.valuation import router as valuation_router
from app.core.config import settings
from app.core.database import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(valuation_router, prefix=settings.API_V1_PREFIX)
app.include_router(scraper_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"message": "AI Car Valuation API", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
