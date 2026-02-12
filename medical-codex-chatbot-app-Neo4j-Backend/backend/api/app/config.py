"""Application configuration powered by environment variables."""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global API settings loaded from the project .env file."""

    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DB")
    default_dataset_tag: str | None = Field(default=None, alias="DEFAULT_DATASET_TAG")
    request_timeout_s: float = Field(default=30.0, alias="NEO4J_REQUEST_TIMEOUT_S")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor suitable for FastAPI dependency injection."""
    return Settings()
