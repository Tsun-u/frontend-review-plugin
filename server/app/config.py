from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    review_api_master_key: str
    postgres_dsn: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "review-assets"
    minio_secure: bool = False
    google_psi_api_key: str = ""
    asset_ttl_days: int = 30
    log_level: str = "INFO"
    deepgaze_checkpoint: str = "/app/deepgaze_checkpoints/DeepGazeIIE.pth"


settings = Settings()
