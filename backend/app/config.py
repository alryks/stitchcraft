from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    prolog_url: str = "http://prolog:8080"
    palettes_dir: str = "/palettes"
    max_upload_mb: int = 12
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

