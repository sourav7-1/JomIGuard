from decimal import Decimal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    test_database_url: str
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str

    # web / frontend CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                import json

                return json.loads(v)
            return [s.strip() for s in v.split(",") if s.strip()]
        return v  # type: ignore[return-value]

    # background processing (app/workers): Celery broker; extractor "llm" or "tesseract_regex"
    celery_broker_url: str = "redis://redis:6379/0"
    extractor: str = "llm"
    stale_after_minutes: int = 10

    # vision-LLM extraction (services/extraction); unset = the LLM extractor refuses to run
    llm_provider: str = "anthropic"  # anthropic | gemini
    anthropic_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_price_input_per_mtok: Decimal | None = None  # USD per million input tokens
    llm_price_output_per_mtok: Decimal | None = None  # USD per million output tokens
    llm_daily_budget_usd: Decimal | None = None
    llm_max_tokens: int = 8192
    gemini_api_key: SecretStr | None = None
    gemini_model: str | None = None
    gemini_max_retries: int = 5  # HTTP 429 (free-tier rate limit): back off and retry
    llm_budget_file: str = "../data/llm/spend.json"  # relative to the working directory
    llm_cache_dir: str = "../data/cache/llm"


settings = Settings()
