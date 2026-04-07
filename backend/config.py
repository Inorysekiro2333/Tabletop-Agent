from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "mysql+pymysql://user:password@localhost:3306/tabletop_agent"

    # JWT
    jwt_secret_key: str = "change-this-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # API
    api_prefix: str = "/api"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
