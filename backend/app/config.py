from pydantic_settings import BaseSettings

class Config(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-live-2.5-flash-native-audio"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-001"
    
    # Vertex AI specific settings
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_GENAI_USE_VERTEXAI: bool = False
    
    # Advanced capabilities
    ENABLE_AFFECTIVE_DIALOG: bool = True
   
    
    # Credentials path
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    
    CORS_ORIGINS: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"
    SESSION_TTL_SECONDS: int = 3600

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"

settings = Config()
