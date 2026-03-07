from pydantic_settings import BaseSettings

class Config(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    SESSION_TTL_SECONDS: int = 3600

    class Config:
        env_file = ".env"

settings = Config()
