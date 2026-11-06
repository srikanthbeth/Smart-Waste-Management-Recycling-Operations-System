from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):

    APP_NAME: str = "Smart Waste Management & Recycling Operations System"

    ENVIRONMENT: str = "development"

    DEBUG: bool = True

    DATABASE_URL: str

    TEST_DATABASE_URL: str

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    BOOTSTRAP_ADMIN_EMAIL: str = "admin@smartwaste.com"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings():

    return Settings()


settings = get_settings()