import logging
import asyncio
from typing import Dict
import time
import re
import json

from fastapi import WebSocket

from app.models.negotiation import NegotiationSession, NegotiationState
from app.services.gemini_client import (
    open_live_session,
    send_vision_frame,
    send_audio_chunk,
    receive_responses,
    monitor_session_lifetime,
    handle_gemini_text,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Valid messages per state
VALID_MESSAGES: Dict[NegotiationState, list[str]] = {
    NegotiationState.IDLE:      ["PRIVACY_CONSENT_GRANTED"],
    NegotiationState.CONSENTED: ["START_NEGOTIATION"],
    NegotiationState.ACTIVE:    ["VISION_FRAME", "AUDIO_CHUNK", "END_NEGOTIATION"],
    NegotiationState.ENDING:    [],
}

# Error codes per state
ERROR_CODES: Dict[NegotiationState, Dict[str, str]] = {
    NegotiationState.IDLE:      {"code": "NOT_CONSENTED",   "message": "Please accept privacy terms first."},
    NegotiationState.CONSENTED: {"code": "NOT_STARTED",     "message": "Start a negotiation session first."},
    NegotiationState.ACTIVE:    {"code": "ALREADY_ACTIVE",  "message": "Session already in progress."},
    NegotiationState.ENDING:    {"code": "SESSION_ENDING",  "message": "Session is ending, please wait."},
}

class NegotiationEngine:
    @staticmethod
    async def validate_message(
        websocket: WebSocket,
        session: NegotiationSession,
        message_type: str
    ) -> bool:
        allowed = VALID_MESSAGES.get(session.state, [])
        if message_type not in allowed:
            # Silently drop early audio chunks to prevent log spam and frontend errors
            if message_type == "AUDIO_CHUNK" and session.state in (NegotiationState.IDLE, NegotiationState.CONSENTED):
                return False

            error = ERROR_CODES.get(session.state, {"code": "INVALID_STATE", "message": "Invalid operation."})
            await websocket.send_json({"type": "ERROR", "payload": error})
            logger.warning(
                f"Rejected {message_type} in state {session.state} "
                f"[session={session.session_id}]"
            )
            return False
        return True

    @staticmethod
    async def transition_state(
        session: NegotiationSession,
        new_state: NegotiationState,
        websocket: WebSocket
    ) -> None:
        old_state = session.state
        session.state = new_state
        logger.info(f"State: {old_state} → {new_state} [session={session.session_id}]")

    @staticmethod
    async def handle_consent(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        session.consent_version = payload.get("version", "1.0")
        session.consent_mode = payload.get("mode", "live")
        await NegotiationEngine.transition_state(session, NegotiationState.CONSENTED, websocket)
        await websocket.send_json({
            "type": "CONSENT_ACKNOWLEDGED",
            "payload": {
                "mode": session.consent_mode,
                "recording_active": True
            }
        })

    @staticmethod
    async def handle_start(session: NegotiationSession, payload: dict, websocket: WebSocket, api_key: str) -> None:
        context = payload.get("context", "")
        session.context = context
        
        await NegotiationEngine.transition_state(session, NegotiationState.ACTIVE, websocket)
        
        try:
            live_session_cm = open_live_session(api_key=api_key, context=context)
            session.live_session_cm = live_session_cm
            session.live_session = await live_session_cm.__aenter__()
            
            asyncio.create_task(receive_responses(session.live_session, websocket, session.session_id))
            asyncio.create_task(monitor_session_lifetime(session, websocket, api_key))
            
            await websocket.send_json({
                "type": "SESSION_STARTED",
                "payload": {
                    "session_id": session.session_id,
                    "model": settings.GEMINI_MODEL,
                    "features": {
                        "audio": True,
                        "vision": True,
                        "web_search": True
                    }
                }
            })
        except Exception as e:
            logger.error(f"Failed to start Gemini session: {e}", exc_info=True)
            await websocket.send_json({
                "type": "ERROR",
                "payload": {"code": "GEMINI_UNAVAILABLE", "message": "AI service unavailable. Please try again."}
            })
            await NegotiationEngine.transition_state(session, NegotiationState.IDLE, websocket)

    @staticmethod
    async def handle_vision_frame(session: NegotiationSession, payload: dict) -> None:
        if session.live_session:
            image_b64 = payload.get("image", "")
            if image_b64:
                await send_vision_frame(session.live_session, image_b64, session.session_id)

    @staticmethod
    async def handle_audio_chunk(session: NegotiationSession, raw_bytes: bytes) -> None:
        if session.live_session:
            await send_audio_chunk(session.live_session, raw_bytes, session.session_id)

    @staticmethod
    async def handle_end(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        await NegotiationEngine.transition_state(session, NegotiationState.ENDING, websocket)
        
        session.final_price = payload.get("final_price")
        session.initial_price = payload.get("initial_price")
        
        if getattr(session, "live_session_cm", None):
            try:
                await session.live_session_cm.__aexit__(None, None, None)
            except Exception:
                pass
            session.live_session = None

        await websocket.send_json({
            "type": "OUTCOME_SUMMARY",
            "payload": {
                "deal_reached": session.final_price is not None,
                "initial_price": session.initial_price,
                "final_price": session.final_price,
                "savings": None,
                "savings_percentage": None,
                "market_value": None,
                "vs_market": None,
                "negotiation_duration_seconds": 0,
                "key_moves": [],
                "effectiveness_score": 0.0,
                "transcript_summary": ""
            }
        })
        await NegotiationEngine.transition_state(session, NegotiationState.IDLE, websocket)

    @staticmethod
    async def route_message(websocket: WebSocket, session: NegotiationSession, msg_type: str, payload: dict) -> None:
        if msg_type == "PRIVACY_CONSENT_GRANTED":
            await NegotiationEngine.handle_consent(session, payload, websocket)
        elif msg_type == "START_NEGOTIATION":
            await NegotiationEngine.handle_start(session, payload, websocket, settings.GEMINI_API_KEY)
        elif msg_type == "VISION_FRAME":
            await NegotiationEngine.handle_vision_frame(session, payload)
        elif msg_type == "END_NEGOTIATION":
            await NegotiationEngine.handle_end(session, payload, websocket)
        else:
            logger.warning(f"Unknown message type {msg_type}")

def _build_context_summary(session: NegotiationSession) -> str:
    original = session.context or ""
    last_strategy = {}
    if session.strategy_history:
        last_strategy = session.strategy_history[-1]
    
    summary = f"Original Context: {original}\n"
    if last_strategy:
        summary += f"Last Strategy: {json.dumps(last_strategy)}\n"
        
    recent_transcript = session.transcript[-10:] if session.transcript else []
    if recent_transcript:
        summary += "Recent Transcript:\n"
        for entry in recent_transcript:
            speaker = entry.get("speaker", "Unknown")
            text = entry.get("text", "")
            summary += f"{speaker}: {text}\n"
            
    return summary
