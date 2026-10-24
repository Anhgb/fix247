"""
Fix 24/7 API – Application Settings
All configuration via environment variables; no hardcoded secrets.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = Field(..., description="asyncpg DSN")
    database_url_sync: str = Field(..., description="psycopg2 DSN for Alembic")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_bucket_media: str = "fix247-media"
    minio_bucket_public: str = "fix247-public"

    # JWT
    jwt_secret: str = Field(..., description="256-bit random secret")
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 30

    # Encryption (AES-256-GCM for CCCD)
    encryption_key: str = Field(..., description="32-byte hex-encoded key")

    # Provider selection
    provider_otp: Literal["mock", "esms", "twilio"] = "mock"
    provider_ai: Literal["mock", "gemini", "openai"] = "mock"
    provider_maps: Literal["mock", "googlemaps", "goong"] = "mock"
    provider_push: Literal["mock", "fcm", "webpush"] = "mock"
    provider_payment: Literal["mock", "vietqr", "momo", "vnpay"] = "mock"

    # AI Keys
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # Business rules (defaults, can be overridden in platform_config table)
    default_commission_rate: float = 0.10
    default_night_surcharge: int = 15000  # VND
    default_survey_fee: int = 30000  # VND
    default_travel_fee: int = 20000  # VND
    dispatch_radius_km: float = 3.0
    dispatch_expand_radius_km: float = 5.0
    dispatch_timeout_seconds: int = 60
    dispatch_expand_timeout_seconds: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
