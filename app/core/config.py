from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "LUMI Backend"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "lumi"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lumi"
    TIMESCALEDB_URL: str = "postgresql://postgres:postgres@localhost:5432/lumi"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    ENERGY_CACHE_TTL: int = 86400  # 24 hours in seconds

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Algorithm constants
    TAU_R: float = 18.2  # Process S rise constant (hours)
    TAU_D: float = 4.2  # Process S decay constant (hours)
    A_C: float = 0.1333  # Circadian amplitude constant
    SLEEP_DEBT_WINDOW: int = 14  # Sliding window in days
    SLEEP_DEBT_WARNING_THRESHOLD: float = 300.0  # 5 hours in minutes

    # Process C harmonic amplitudes
    HARMONIC_AMPLITUDES: list[float] = [0.97, 0.22, 0.07, 0.03, 0.001]
    CIRCADIAN_PERIOD: float = 24.2  # Natural circadian period (hours)

    class Config:
        env_file = ".env"


settings = Settings()
