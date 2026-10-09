from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str
    test_database_url: str
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str


settings = Settings()
