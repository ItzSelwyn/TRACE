from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://trace:trace@localhost:5432/trace"
    DATABASE_URL_SYNC: str = "postgresql://trace:trace@localhost:5432/trace"
    IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER: float = 1.5
    IDENTITY_CONFIRM_THRESHOLD: float = 0.70
    IDENTITY_CANDIDATE_THRESHOLD: float = 0.40
    ANALYTICS_WINDOW_SECONDS: int = 300
    JWT_SECRET: str = "changeme"
    JWT_EXPIRY_MINUTES: int = 480
    JWT_ALGORITHM: str = "HS256"
    ALLOW_ANON_DEMO: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
