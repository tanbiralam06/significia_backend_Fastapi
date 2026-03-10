from typing import Any, Dict, Optional
from pydantic import PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Significia API"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_USER: str = "significia"
    POSTGRES_PASSWORD: str = "significia"
    POSTGRES_DB: str = "significia"
    POSTGRES_PORT: str = "5432"
    
    REDIS_HOST: str = "redis"
    REDIS_PORT: str = "6379"

    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "change-this-to-a-secure-32-byte-base64-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
