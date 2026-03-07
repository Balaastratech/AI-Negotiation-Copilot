from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Negotiation Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting AI Negotiation Copilot with primary model: {settings.GEMINI_MODEL}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health")
async def health_check_root():
    return {"status": "healthy"}

from app.api.websocket import router as websocket_router
app.include_router(websocket_router)
