from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./sfdap_dev.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = True
    API_TITLE: str = "SFDAP - Akilli Tarim Veri Analizi Platformu API"
    API_VERSION: str = "1.0.0"
    API_KEY: str = "dev-api-key"
    SECRET_KEY: str = "dev-secret-key"
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    MODEL_PATH: str = "app/ml/models/"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
