from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Car Valuation"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5434/car_valuation"

    SECRET_KEY: str = "change-me-in-production"
    REFRESH_SECRET_KEY: str = "change-me-refresh-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GEMINI_API_KEY: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


settings = Settings()
