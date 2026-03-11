import logging
import asyncio
from typing import Dict
import time
import re
import json

from fastapi import WebSocket
from google.genai import types

from app.models.negotiation import NegotiationSession, NegotiationState
from app.services.gemini_client import (
    open_live_session,
    send_vision_frame,
    send_audio_chunk,
    receive_responses,
    monitor_session_lifetime,
    handle_gemini_text,
)
from app.services.audio_buffer import AudioBuffer
from app.services.listener_agent import ListenerAgent
from app.config import settings

logger = logging.getLogger(__name__)

# Valid messages per state
VALID_MESSAGES: Dict[NegotiationState, list[str]] = {
    NegotiationState.IDLE:      ["PRIVACY_CONSENT_GRANTED"],
    NegotiationState.CONSENTED: ["START_NEGOTIATION"],
    NegotiationState.ACTIVE:    ["VISION_FRAME", "AUDIO_CHUNK", "END_NEGOTIATION", "STATE_UPDATE", "ASK_ADVICE", "SPEAKER_IDENTIFIED", "SPEAKER_STOPPED"],
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
        
        # Broadcast state transition to frontend
        await websocket.send_json({
            "type": "NEGOTIATION_STATE_CHANGED",
            "payload": {
                "previous_state": old_state.value,
                "current_state": new_state.value,
                "timestamp": time.time()
            }
        })

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
        user_context = payload.get("user_context", {})
        session.context = context
        session.user_context = user_context

        await NegotiationEngine.transition_state(session, NegotiationState.ACTIVE, websocket)

        try:
            live_session_cm = open_live_session(api_key=api_key, context=context)
            session.live_session_cm = live_session_cm
            session.live_session = await live_session_cm.__aenter__()

            # ── Dual-Model: initialise buffer + listener ─────────────────────
            audio_buffer = AudioBuffer(max_seconds=90)
            session.audio_buffer = audio_buffer

            listener = ListenerAgent(
                session_id=session.session_id,
                audio_buffer=audio_buffer,
                gemini_send_lock=session.gemini_send_lock,
                websocket=websocket,
            )
            session.listener_agent = listener
            listener.start()
            # ─────────────────────────────────────────────────────────────────

            asyncio.create_task(receive_responses(session.live_session, websocket, session.session_id, session))
            asyncio.create_task(monitor_session_lifetime(session, websocket, api_key))

            await websocket.send_json({
                "type": "SESSION_STARTED",
                "payload": {
                    "session_id": session.session_id,
                    "model": settings.GEMINI_MODEL,
                    "features": {
                        "audio": True,
                        "vision": True,
                        "web_search": True,
                        "dual_model": True,
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
            # Push audio to rolling buffer (for ListenerAgent)
            if session.audio_buffer:
                session.audio_buffer.push(raw_bytes)

            # Only send audio to the Live model if the advisor is active.
            # Otherwise, the Live model will hear the conversation and try to respond proactively (VAD),
            # consuming the conversational turn and breaking the flow.
            if getattr(session, 'advisor_active', False):
                # Acquire the send lock to prevent concurrent send_realtime_input calls
                # (audio vs. advisor text) which cause Gemini WebSocket error 1007.
                async with session.gemini_send_lock:
                    await send_audio_chunk(session.live_session, raw_bytes, session.session_id)

    @staticmethod
    async def handle_end(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        await NegotiationEngine.transition_state(session, NegotiationState.ENDING, websocket)

        session.final_price = payload.get("final_price")
        session.initial_price = payload.get("initial_price")

        # Stop listener agent first so it stops referencing the live session
        if session.listener_agent:
            await session.listener_agent.stop()
            session.listener_agent = None

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
    async def handle_state_update(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        """
        Handle STATE_UPDATE message from AI.
        AI extracts negotiation context from transcript and sends updates.

        Args:
            session: Current negotiation session
            payload: State updates from AI (item, prices, etc.)
            websocket: WebSocket connection to forward to frontend
        """
        logger.info(f"AI state update received [session={session.session_id}]: {payload}")

        # Forward state update to frontend
        await websocket.send_json({
            "type": "STATE_UPDATE",
            "payload": payload
        })


    @staticmethod
    async def handle_speaker_identified(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        """
        Handle SPEAKER_IDENTIFIED message from frontend voice fingerprinting.
        
        Updates the current speaker label and flushes any buffered transcripts
        with the correct speaker label.
        
        Args:
            session: Current negotiation session
            payload: Contains speaker label ('user' or 'counterparty') and timestamp (in milliseconds)
            websocket: WebSocket connection for sending buffered transcripts
        """
        speaker = payload.get("speaker", "user")
        timestamp_ms = payload.get("timestamp", time.time() * 1000)
        
        # Convert frontend timestamp from milliseconds to seconds
        timestamp = timestamp_ms / 1000.0
        
        # Detect speaker change
        speaker_changed = session.current_speaker != speaker
        is_first_identification = session.speaker_last_updated == 0
        
        # Store current speaker in session
        session.current_speaker = speaker
        session.speaker_last_updated = timestamp
        
        if is_first_identification:
            logger.info(f"✓ First speaker identified: {speaker.upper()} [session={session.session_id}]")
        elif speaker_changed:
            logger.info(f"✓ Speaker changed: {session.current_speaker.upper()} → {speaker.upper()} [session={session.session_id}]")
        else:
            logger.info(f"✓ Speaker confirmed: {speaker.upper()} [session={session.session_id}]")
        
        # Flush any buffered transcripts with the correct speaker label
        if session.pending_transcripts:
            logger.info(f"🔓 Flushing {len(session.pending_transcripts)} buffered transcripts with speaker={speaker.upper()} [session={session.session_id}]")
            
            for idx, buffered_transcript in enumerate(session.pending_transcripts, 1):
                # Update speaker label
                buffered_transcript["speaker"] = speaker
                
                logger.info(f"   Flushing transcript {idx}/{len(session.pending_transcripts)}: '{buffered_transcript['text'][:50]}...' as {speaker.upper()} [session={session.session_id}]")
                
                # Send to frontend
                await websocket.send_json({
                    "type": "TRANSCRIPT_UPDATE",
                    "payload": buffered_transcript
                })
            
            # Clear buffer
            session.pending_transcripts = []
            logger.info(f"✅ Buffer cleared [session={session.session_id}]")

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
        elif msg_type == "STATE_UPDATE":
            # Button-triggered system: AI sends state updates
            await NegotiationEngine.handle_state_update(session, payload, websocket)
        elif msg_type == "ASK_ADVICE":
            # Button-triggered system: User requests AI advice
            await NegotiationEngine.handle_ask_advice(session, payload, websocket)
        elif msg_type == "SPEAKER_IDENTIFIED":
            # Voice fingerprinting: Frontend identified speaker
            await NegotiationEngine.handle_speaker_identified(session, payload, websocket)
        elif msg_type == "SPEAKER_STOPPED":
            # VAD: User stopped speaking
            await NegotiationEngine.handle_speaker_stopped(session, websocket)
        else:
            logger.warning(f"Unknown message type {msg_type}")
    @staticmethod
    async def handle_speaker_stopped(session: NegotiationSession, websocket: WebSocket) -> None:
        """
        No-op. Frontend VAD stopping chunk delivery is enough to prevent 1007 bounds crash.
        Sending turn_complete=True here forces unwanted AI responses and burns tokens.
        """
        pass

    @staticmethod
    async def handle_ask_advice(session: NegotiationSession, payload: dict, websocket: WebSocket) -> None:
        """
        Handle ASK_ADVICE message from frontend.

        Injects a text advice query into the running Gemini Live session using
        send_client_content(), which IS supported on native audio models.

        HOW IT WORKS (native audio model behaviour):
        - Text in  → send_client_content(turn_complete=True)
        - Audio out ← model responds with spoken advice
        - Session continues streaming audio normally after

        WHY WE SEND activity_end FIRST:
        While audio streaming, the session has an ongoing input turn.
        Sending send_client_content mid-stream without closing the audio turn
        causes the two inputs to compete → model gets confused → empty response.
        Sending activity_end first lets Gemini close the current audio turn cleanly,
        then our text query becomes the sole pending input it needs to respond to.
        """
        logger.info(f"ASK_ADVICE request received [session={session.session_id}]")
        
        # User requested advice — allow Gemini Live's audio output to reach the frontend speaker
        session.advisor_active = True

        live_session = session.live_session
        if not live_session:
            logger.error(f"No active Gemini session [session={session.session_id}]")
            await websocket.send_json({
                "type": "ERROR",
                "payload": {"message": "No active Gemini session"}
            })
            return

        # Notify frontend immediately — user sees "AI is thinking..."
        await websocket.send_json({"type": "AI_THINKING", "payload": {}})

        try:
            # ── 1. Build the rich advisor query ──────────────────────────────
            listener_ctx = session.listener_agent.last_context if session.listener_agent else {}
            user_ctx = session.user_context or {}

            state_for_query = {
                "item":         listener_ctx.get("item") or user_ctx.get("item", ""),
                "seller_price": listener_ctx.get("seller_price") or user_ctx.get("seller_price"),
                "target_price": user_ctx.get("target_price"),
                "max_price":    user_ctx.get("max_price"),
            }

            # Extract the raw formatted transcript from the frontend ASK_ADVICE payload
            frontend_transcript = payload.get("state", {}).get("transcript", "")

            from app.services.gemini_client import build_advisor_query
            # Pass the frontend_transcript string down instead of the empty session.transcript list
            query = build_advisor_query(state_for_query, transcript=frontend_transcript)

            # Append listener intel (leverage points, sentiment, live transcript)
            if session.listener_agent:
                agent = session.listener_agent
                extras = []
                if agent.last_context.get("leverage_points"):
                    extras.append("Leverage: " + "; ".join(agent.last_context["leverage_points"]))
                if agent.last_context.get("sentiment"):
                    extras.append(f"Sentiment: {agent.last_context['sentiment']}")
                if agent.accumulated_transcript:
                    extras.append(
                        f'Live transcript snippet (last 400 chars):\n'
                        f'"{agent.accumulated_transcript[-400:]}"'
                    )
                if extras:
                    query += "\n\n[LISTENER INTEL]\n" + "\n".join(extras)

            logger.info(
                f"ADVISOR_QUERY ({len(query)} chars): "
                f"{query[:150]}... [session={session.session_id}]"
            )

            # ── 2. Inject into Live session (hold lock so audio can't compete) ──
            #
            # Sequence:
            #   a) activity_end  → tells Gemini the current audio input turn is done
            #   b) send_client_content(turn_complete=True)  → the advice query
            #
            # The lock is held the entire time so no concurrent send_realtime_input
            # (audio) calls interrupt between steps (a) and (b).
            async with session.gemini_send_lock:
                # Close the ongoing audio input turn cleanly
                await live_session.send_realtime_input(
                    activity_end=types.ActivityEnd()
                )
                logger.debug(f"ActivityEnd sent [session={session.session_id}]")

                # Brief yield to let the event loop process the activity_end
                await asyncio.sleep(0.05)

                # Inject text query — model responds with spoken audio advice
                await live_session.send_client_content(
                    turns=types.Content(
                        role="user",
                        parts=[types.Part(text=query)]
                    ),
                    turn_complete=True
                )

                # Re-open audio input so the conversation resumes after AI speaks
                await live_session.send_realtime_input(
                    activity_start=types.ActivityStart()
                )
                logger.debug(f"ActivityStart sent [session={session.session_id}]")

            logger.info(
                f"ADVISOR_QUERY injected via send_client_content "
                f"[session={session.session_id}]"
            )

        except Exception as e:
            logger.error(f"Failed to inject advice query: {e}", exc_info=True)
            await websocket.send_json({
                "type": "ERROR",
                "payload": {"message": str(e)}
            })
            await websocket.send_json({"type": "AI_LISTENING", "payload": {}})


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
