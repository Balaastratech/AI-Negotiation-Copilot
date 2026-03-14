from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
import logging
from asgi_correlation_id.middleware import CorrelationIdMiddleware
from typing import Dict, Any

from app.config import settings
from app.utils.logging_config import setup_logging

setup_logging(log_level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Negotiation Copilot", version="1.0.0")

app.add_middleware(CorrelationIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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

frontend_logger = logging.getLogger("frontend")

@app.post("/api/log")
async def log_frontend_message(request: Request, payload: Dict[str, Any] = Body(...)):
    # The correlation ID is automatically picked up by the logger from the request context
    frontend_logger.info(payload.get("message", "No message"), extra=payload)
    return {"status": "logged"}


from app.api.websocket import router as websocket_router
app.include_router(websocket_router)
