from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Manages application settings and environment variables."""
    ALPHA_VANTAGE_API_KEY: str
    FINNHUB_API_KEY: str
    FRED_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    API_KEY: str
    SCHEDULER_INTERVAL_HOURS: int = 4

    # Service URLs for scheduler
    ECONOMIC_SERVICE_URL: str
    SENTIMENT_SERVICE_URL: str
    TECHNICALS_SERVICE_URL: str
    CROSS_ASSET_SERVICE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
