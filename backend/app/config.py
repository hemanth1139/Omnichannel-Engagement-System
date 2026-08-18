from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://username:password@localhost:5432/postgres"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    APP_ENV: str = "development"
    HCP_PROFILE_TABLE_NAME: str = "hcp_profile"
    MODEL_OUTPUT_TABLE_NAME: str = "model_output"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
