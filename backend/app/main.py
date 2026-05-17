from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
# noqa: models must be imported before alembic can detect them
import app.models  # noqa: F401
from app.api.scraper import router as scraper_router
from app.api.subscription import router as subscription_router
from app.api.valuation import router as valuation_router
from app.core.config import settings

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
app.include_router(subscription_router, prefix=settings.API_V1_PREFIX)
app.include_router(scraper_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


FRONTEND_DIR = Path("/app/frontend_dist")
INDEX_FILE = FRONTEND_DIR / "index.html"

if INDEX_FILE.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIR / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(request: Request, full_path: str):
        # Serve any file that exists in the dist (e.g. favicon, robots.txt),
        # otherwise fall back to index.html so React Router can route client-side.
        candidate = FRONTEND_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(INDEX_FILE)
else:
    @app.get("/")
    def root():
        return {"message": "AI Car Valuation API", "docs": "/docs"}
