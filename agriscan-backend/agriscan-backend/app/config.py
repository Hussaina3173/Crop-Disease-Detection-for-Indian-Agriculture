from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://agriscan_user:agriscan_pass@localhost:5432/agriscan"

    # JWT
    jwt_secret_key: str = "change-this-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    reset_token_expire_minutes: int = 15

    # Storage
    storage_backend: str = "local"  # "local" or "s3"
    local_upload_dir: str = "uploads"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_s3_bucket: str | None = None
    aws_region: str = "ap-south-1"

    # Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@agriscan.app"

    # CORS
    frontend_origin: str = "http://localhost:5500"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
