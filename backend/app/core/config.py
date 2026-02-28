from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "dev"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production-use-256-bit-random-key"
    app_name: str = "CHM_KRYPTON"
    app_version: str = "1.0.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = (
        "https://web.telegram.org,"
        "https://k.web.telegram.org,"
        "http://localhost:5173,"
        "http://localhost:4173,"
        "http://localhost:3000"
    )

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "password"
    db_name: str = "chm_krypton"
    database_url: Optional[str] = None  # Может быть задан напрямую (Railway)

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: Optional[str] = None  # Может быть задан напрямую

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webapp_url: str = "https://your-frontend-url"
    super_admin_tg_id: int = 0

    # Bybit
    bybit_master_api_key: str = ""
    bybit_master_api_secret: str = ""
    bybit_master_min_balance: float = 10_000.0
    bybit_demo_base_url: str = "https://api-demo.bybit.com"
    bybit_real_base_url: str = "https://api.bybit.com"

    # JWT
    jwt_secret: str = "change-me-jwt-secret-256-bit"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    # AES Encryption (для API ключей биржи)
    aes_encryption_key: str = "0123456789abcdef0123456789abcdef"  # 32 байта hex

    # Referral settings
    referral_level1_pct: float = 10.0   # 10% от суммы покупки
    referral_level2_pct: float = 3.0    # 3% от суммы покупки
    referral_payout_days: int = 7        # выплата каждые N дней

    # Payout settings
    min_payout_amount: float = 50.0      # минимальная сумма выплаты в USDT

    # Rate limiting
    rate_limit_per_minute: int = 100
    rate_limit_trading_per_minute: int = 10

    # ChallengeEngine
    engine_check_interval_seconds: int = 30

    @property
    def database_url_async(self) -> str:
        if self.database_url:
            url = self.database_url
            url = url.replace("postgres://", "postgresql+asyncpg://")
            if url.startswith("postgresql://") and "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://")
            return url
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Синхронный URL для Alembic."""
        if self.database_url:
            url = self.database_url
            url = url.replace("postgres://", "postgresql://")
            url = url.replace("postgresql+asyncpg://", "postgresql://")
            return url
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_connection_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Переопределяем redis_url для обратной совместимости
    @field_validator("redis_url", mode="before")
    @classmethod
    def assemble_redis_url(cls, v):
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
