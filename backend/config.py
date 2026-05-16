from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database — 默认 PostgreSQL，兼容 MySQL
    # 实际凭据请在 backend/.env 中配置，不要写进代码
    database_url: str = "postgresql+psycopg://postgres:changeme@localhost:5432/hello_golang"

    # Redis — 会话缓存（优雅降级，不可用时不影响运行）
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 86400  # 24 hours

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
