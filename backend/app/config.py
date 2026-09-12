from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://trace:trace@127.0.0.1:5432/trace"
    DATABASE_URL_SYNC: str = "postgresql://trace:trace@127.0.0.1:5432/trace"
    IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER: float = 1.5
    IDENTITY_CONFIRM_THRESHOLD: float = 0.70
    IDENTITY_CANDIDATE_THRESHOLD: float = 0.40
    ANALYTICS_WINDOW_SECONDS: int = 300
    JWT_SECRET: str = "changeme"
    JWT_EXPIRY_MINUTES: int = 480
    JWT_ALGORITHM: str = "HS256"
    ALLOW_ANON_DEMO: bool = True

    # ---------------------------------------------------------------------------
    # Multi-modal identity fusion weights
    # CityFlowV2 / visual-only mode (used when plates are unavailable)
    # ---------------------------------------------------------------------------
    IDENTITY_APPEARANCE_WEIGHT: float = 0.55
    IDENTITY_TEMPORAL_WEIGHT: float = 0.25
    IDENTITY_CAMERA_TRANSITION_WEIGHT: float = 0.15
    IDENTITY_COLOUR_WEIGHT: float = 0.03
    IDENTITY_TYPE_WEIGHT: float = 0.02

    # ANPR-capable mode (used when BOTH observations have readable plates)
    IDENTITY_PLATE_WEIGHT: float = 0.35
    IDENTITY_APPEARANCE_WEIGHT_ANPR: float = 0.30
    IDENTITY_TEMPORAL_WEIGHT_ANPR: float = 0.15
    IDENTITY_CAMERA_TRANSITION_WEIGHT_ANPR: float = 0.10
    IDENTITY_COLOUR_WEIGHT_ANPR: float = 0.05
    IDENTITY_TYPE_WEIGHT_ANPR: float = 0.05

    # ---------------------------------------------------------------------------
    # Vehicle Appearance / Re-ID Feature Extractor Settings
    # ---------------------------------------------------------------------------
    APPEARANCE_REID_ENABLED: bool = True
    APPEARANCE_MODEL_NAME: str = "resnet34_veri776"  # "resnet34_veri776" or "mobilenet_v3_small"
    APPEARANCE_MODEL_PATH: str = "models/resnet34_veri776_deploy.pt"
    APPEARANCE_EMBEDDING_DIM: int = 512
    APPEARANCE_DEVICE: str = "auto"  # "auto", "cpu", "cuda"
    APPEARANCE_MIN_CROP_SIZE: int = 24
    APPEARANCE_MAX_TRACK_SAMPLES: int = 5
    APPEARANCE_COSINE_MIN: float = 0.60
    APPEARANCE_COSINE_MAX: float = 0.88

    # Perception / Detection model
    YOLO_MODEL_PATH: str = "models/yolov8n.pt"

    model_config = {
        "env_file": [".env", "../.env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()

