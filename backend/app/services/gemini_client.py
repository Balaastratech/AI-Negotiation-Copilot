import os
import time
import json
import base64
import asyncio
import logging
import re
from contextlib import asynccontextmanager

from google import genai
from google.genai import types
from fastapi import WebSocket

from app.models.negotiation import NegotiationSession, NegotiationState
from app.config import settings
from app.services.master_prompt import MASTER_NEGOTIATION_PROMPT

logger = logging.getLogger(__name__)

GEMINI_MODEL_PRIMARY = settings.GEMINI_MODEL
GEMINI_MODEL_FALLBACK = settings.GEMINI_MODEL_FALLBACK
GEMINI_MODEL_TEXT_ONLY = "gemini-2.0-flash"

SESSION_HARD_LIMIT_SECONDS = 600
SESSION_HANDOFF_TRIGGER = 540

class GeminiUnavailableError(Exception):
    """Raised when all Gemini Live API models are unavailable."""
    pass


def _build_context_summary(session: NegotiationSession) -> str:
    """Build a context summary for session handoff"""
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

def build_system_prompt(context: str) -> str:
    return MASTER_NEGOTIATION_PROMPT.replace("{context}", context)

async def handle_gemini_text(websocket: WebSocket, session_id: str, text: str) -> None:
    """Handle text responses from Gemini, extracting strategy updates and AI responses."""
    STRATEGY_PATTERN = re.compile(r'<strategy>(.*?)</strategy>', re.DOTALL)
    
    strategies = STRATEGY_PATTERN.findall(text)
    for strategy_str in strategies:
        try:
            strategy_data = json.loads(strategy_str)
            await websocket.send_json({
                "type": "STRATEGY_UPDATE",
                "payload": strategy_data
            })
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse strategy JSON from session {session_id}: {strategy_str}")
            
    remaining_text = STRATEGY_PATTERN.sub('', text).strip()
    
    if remaining_text:
        await websocket.send_json({
            "type": "AI_RESPONSE",
            "payload": {
                "response_type": "coaching",
                "text": remaining_text,
                "timestamp": time.time()
            }
        })

class GeminiClient:
    @staticmethod
    @asynccontextmanager
    async def open_live_session(api_key: str, context: str, model: str = GEMINI_MODEL_PRIMARY):
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
        if settings.GOOGLE_CLOUD_PROJECT:
            os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GOOGLE_CLOUD_PROJECT

        if settings.GOOGLE_GENAI_USE_VERTEXAI:
            client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION
            )
        else:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version='v1alpha'),
            )
        
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=build_system_prompt(context),
            
            # Generation config for faster, shorter responses
            generation_config=types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=150,  # Limit response length for speed
                candidate_count=1
            ),
            
            # Disable features that add latency
            enable_affective_dialog=False,
            
            # Enable transcriptions
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig()
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
            # Validate audio format before sending
            chunk_size = len(raw_pcm_bytes)
            
            # Check for odd byte count (incomplete Int16 sample)
            if chunk_size % 2 != 0:
                logger.error(f"AUDIO FORMAT ERROR: Odd byte count {chunk_size} - incomplete Int16 sample! [{session_id}]")
                return
            
            # Check for empty chunks
            if chunk_size == 0:
                logger.warning(f"Empty audio chunk received [{session_id}]")
                return
            
            # Log chunk statistics periodically (every 100th chunk)
            if not hasattr(send_audio_chunk, '_chunk_counter'):
                send_audio_chunk._chunk_counter = {}
            
            if session_id not in send_audio_chunk._chunk_counter:
                send_audio_chunk._chunk_counter[session_id] = 0
            
            send_audio_chunk._chunk_counter[session_id] += 1
            
            if send_audio_chunk._chunk_counter[session_id] % 100 == 0:
                sample_count = chunk_size // 2
                duration_ms = (sample_count / 16000) * 1000
                logger.info(f"Audio stats: chunk #{send_audio_chunk._chunk_counter[session_id]}, "
                           f"{chunk_size} bytes, {sample_count} samples, {duration_ms:.1f}ms @ 16kHz [{session_id}]")
            
            blob = types.Blob(data=raw_pcm_bytes, mime_type="audio/pcm;rate=16000")
            await live_session.send_realtime_input(audio=blob)
        except Exception as e:
            logger.error(f"Audio chunk send failed [{session_id}]: {e}")

    @staticmethod
    async def receive_responses(live_session, websocket: WebSocket, session_id: str) -> None:
        """
        Receive responses from Gemini Live API.

        IMPORTANT: The receive() iterator ends after each turn_complete.
        We need to call receive() again for each new turn to continue the conversation.
        This is the expected behavior of the Gemini Live API SDK.
        """
        total_responses = 0
        turn_count = 0

        while True:
            try:
                logger.info(f"Starting receive() for turn #{turn_count + 1} [{session_id}]")

                turn_response_count = 0
                turn_complete_received = False

                # Each receive() call handles ONE turn
                # After turn_complete, the iterator ends and we need to call receive() again
                async for response in live_session.receive():
                    total_responses += 1
                    turn_response_count += 1

                    if not response.server_content:
                        continue

                    sc = response.server_content

                    if sc.interrupted:
                        logger.info(f"Interruption detected [{session_id}]")
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
                        logger.debug(f"User transcript: {sc.input_transcription.text} [{session_id}]")
                        await websocket.send_json({
                            "type": "TRANSCRIPT_UPDATE",
                            "payload": {
                                "speaker": "user",
                                "text": sc.input_transcription.text,
                                "timestamp": int(time.time() * 1000)
                            }
                        })
                        # User is speaking, so AI is listening
                        await websocket.send_json({
                            "type": "AI_LISTENING",
                            "payload": {}
                        })

                    # Use output_transcription for Vertex AI
                    output_transcription = getattr(sc, 'output_transcription', None) or getattr(sc, 'output_audio_transcription', None)
                    if output_transcription and output_transcription.text:
                        logger.debug(f"AI transcript: {output_transcription.text} [{session_id}]")
                        # AI is speaking
                        await websocket.send_json({
                            "type": "AI_SPEAKING",
                            "payload": {}
                        })
                        await websocket.send_json({
                            "type": "TRANSCRIPT_UPDATE",
                            "payload": {
                                "speaker": "ai",
                                "text": output_transcription.text,
                                "timestamp": int(time.time() * 1000)
                            }
                        })

                    # Check for turn_complete - this signals the end of this receive() iteration
                    if hasattr(sc, 'turn_complete') and sc.turn_complete:
                        turn_complete_received = True
                        turn_count += 1
                        logger.info(f"✓ Turn {turn_count} complete ({turn_response_count} responses, {total_responses} total) [{session_id}]")
                        # Turn complete means AI finished speaking, now listening for next input
                        await websocket.send_json({
                            "type": "AI_LISTENING",
                            "payload": {}
                        })
                        break  # Exit this receive() loop, will call receive() again for next turn

                # If we exited the loop without turn_complete, something went wrong
                if not turn_complete_received:
                    logger.error(f"⚠ receive() ended without turn_complete after {turn_response_count} responses [{session_id}]")
                    logger.error(f"  This may indicate a connection issue or session closure")
                    try:
                        await websocket.send_json({
                            "type": "AI_DEGRADED",
                            "payload": {"message": "AI connection ended unexpectedly. Please refresh to reconnect."}
                        })
                    except Exception:
                        pass
                    break

                # Turn completed successfully, loop will call receive() again for next turn
                logger.debug(f"Ready for turn #{turn_count + 1}, calling receive() again [{session_id}]")
                await asyncio.sleep(0.01)  # Brief pause before next receive() call

            except asyncio.CancelledError:
                logger.info(f"Receive loop cancelled after {turn_count} turns [{session_id}]")
                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                # Check if this is the audio format error
                if "1007" in error_msg or "invalid frame payload data" in error_msg or "inputaudio" in error_msg:
                    logger.error(f"AUDIO FORMAT ERROR detected [{session_id}]:")
                    logger.error(f"  Error type: {error_type}")
                    logger.error(f"  Error message: {error_msg}")
                    logger.error(f"  This suggests the frontend is sending corrupted or incorrectly formatted audio")
                    logger.error(f"  Expected: 16kHz, signed 16-bit little-endian PCM, mono channel")

                    # Get chunk counter stats
                    if hasattr(send_audio_chunk, '_chunk_counter') and session_id in send_audio_chunk._chunk_counter:
                        logger.error(f"  Total chunks sent before error: {send_audio_chunk._chunk_counter[session_id]}")
                else:
                    logger.error(f"Receive loop error after {turn_count} turns [{session_id}]: {error_type}: {error_msg}", exc_info=True)

                try:
                    await websocket.send_json({
                        "type": "AI_DEGRADED",
                        "payload": {"message": f"AI connection error: {error_msg}"}
                    })
                except Exception:
                    pass
                break  # Exit on exception

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
