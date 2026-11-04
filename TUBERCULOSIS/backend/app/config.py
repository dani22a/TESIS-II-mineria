from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://USER:PASS@localhost:5432/tb_screening"
    jwt_secret: str = "dev-only-change-me-use-a-32-byte-secret!"
    bcrypt_rounds: int = 12
    jwt_ttl_minutes: int = 60
    storage_dir: str = "./storage"
    cors_origins: str = "http://localhost:5173"
    max_upload_bytes: int = 15 * 1024 * 1024
    min_image_side: int = 256
    min_pixel_std: float = 8.0
    decision_threshold: float = 0.5
    seed_password: str = "Demo-Passw0rd!"


settings = Settings()
