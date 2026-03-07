import os
import time
import json
import base64
import asyncio
import logging
from contextlib import asynccontextmanager

from google import genai
from google.genai import types
from fastapi import WebSocket

from app.models.negotiation import NegotiationSession, NegotiationState
from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL_PRIMARY = settings.GEMINI_MODEL
GEMINI_MODEL_FALLBACK = settings.GEMINI_MODEL_FALLBACK
GEMINI_MODEL_TEXT_ONLY = "gemini-2.0-flash"

SESSION_HARD_LIMIT_SECONDS = 600
SESSION_HANDOFF_TRIGGER = 540

class GeminiUnavailableError(Exception):
    """Raised when all Gemini Live API models are unavailable."""
    pass

def build_system_prompt(context: str) -> str:
    return f"You are an expert AI negotiation copilot. The user context: {context}\nProvide concise advice."

class GeminiClient:
    @staticmethod
    @asynccontextmanager
    async def open_live_session(api_key: str, context: str, model: str = GEMINI_MODEL_PRIMARY):
        client = genai.Client(api_key=api_key)
        
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO", "TEXT"],
            tools=[types.Tool(google_search=types.GoogleSearch())],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction=build_system_prompt(context),
            session_resumption=types.SessionResumptionConfig(handle=None),
        )
        
        try:
            async with client.aio.live.connect(model=model, config=config) as session:
                logger.info(f"Gemini Live session opened with model: {model}")
                yield session
        except Exception as e:
            logger.warning(f"Primary model {model} failed: {e}. Trying fallback.")
            
            if model != GEMINI_MODEL_FALLBACK:
                try:
                    async with client.aio.live.connect(
                        model=GEMINI_MODEL_FALLBACK, config=config
                    ) as session:
                        logger.info(f"Gemini Live fallback session opened: {GEMINI_MODEL_FALLBACK}")
                        yield session
                    return
                except Exception as e2:
                    logger.warning(f"Fallback model failed: {e2}")
            
            raise GeminiUnavailableError("All Live API models failed") from e

    @staticmethod
    async def send_vision_frame(live_session, jpeg_base64: str, session_id: str) -> None:
        try:
            image_bytes = base64.b64decode(jpeg_base64)
            blob = types.Blob(data=image_bytes, mime_type="image/jpeg")
            await live_session.send_realtime_input(video=blob)
        except Exception as e:
            logger.warning(f"Vision frame send failed [{session_id}]: {e}")

    @staticmethod
    async def send_audio_chunk(live_session, raw_pcm_bytes: bytes, session_id: str) -> None:
        try:
            blob = types.Blob(data=raw_pcm_bytes, mime_type="audio/pcm;rate=16000")
            await live_session.send_realtime_input(audio=blob)
        except Exception as e:
            logger.warning(f"Audio chunk send failed [{session_id}]: {e}")

    @staticmethod
    async def receive_responses(live_session, websocket: WebSocket, session_id: str) -> None:
        try:
            async for response in live_session.receive():
                if not response.server_content:
                    continue
                
                sc = response.server_content
                
                if sc.interrupted:
                    await websocket.send_json({"type": "AUDIO_INTERRUPTED", "payload": {}})
                    continue
                
                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                            if isinstance(part.inline_data.data, str):
                                pcm_bytes = base64.b64decode(part.inline_data.data)
                            else:
                                pcm_bytes = part.inline_data.data
                            await websocket.send_bytes(pcm_bytes)
                        elif part.text:
                            await handle_gemini_text(websocket, session_id, part.text)
                            
                if sc.input_transcription and sc.input_transcription.text:
                    await websocket.send_json({
                        "type": "TRANSCRIPT_UPDATE",
                        "payload": {
                            "speaker": "user",
                            "text": sc.input_transcription.text,
                            "timestamp": int(time.time() * 1000)
                        }
                    })
                    
                if sc.output_audio_transcription and sc.output_audio_transcription.text:
                    await websocket.send_json({
                        "type": "TRANSCRIPT_UPDATE",
                        "payload": {
                            "speaker": "ai",
                            "text": sc.output_audio_transcription.text,
                            "timestamp": int(time.time() * 1000)
                        }
                    })
        except Exception as e:
            logger.error(f"Gemini receive loop error [{session_id}]: {e}")
            try:
                await websocket.send_json({
                    "type": "AI_DEGRADED",
                    "payload": {"message": "AI connection interrupted. Attempting recovery..."}
                })
            except Exception:
                pass

    @staticmethod
    async def monitor_session_lifetime(session: NegotiationSession, websocket: WebSocket, api_key: str) -> None:
        await asyncio.sleep(SESSION_HANDOFF_TRIGGER)
        
        if session.state != NegotiationState.ACTIVE:
            return
            
        logger.info(f"Session handoff triggered [{session.session_id}]")
        
        context_summary = _build_context_summary(session)
        
        old_live = session.live_session
        if old_live:
            try:
                await old_live.__aexit__(None, None, None)
            except Exception:
                pass
                
        try:
            new_live = await GeminiClient.open_live_session(
                api_key=api_key,
                context=f"{session.context}\n\nCONTINUATION CONTEXT:\n{context_summary}"
            )
            session.live_session = new_live
            
            asyncio.create_task(GeminiClient.receive_responses(new_live, websocket, session.session_id))
            
            logger.info(f"Session handoff complete [{session.session_id}]")
            
            asyncio.create_task(GeminiClient.monitor_session_lifetime(session, websocket, api_key))
        except Exception as e:
            logger.error(f"Failed to hand off session [{session.session_id}]: {e}")

open_live_session = GeminiClient.open_live_session
send_vision_frame = GeminiClient.send_vision_frame
send_audio_chunk = GeminiClient.send_audio_chunk
receive_responses = GeminiClient.receive_responses
monitor_session_lifetime = GeminiClient.monitor_session_lifetime
