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
from app.services.master_prompt import MASTER_NEGOTIATION_PROMPT, ADVISOR_SYSTEM_PROMPT

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
def build_advisor_query(state: dict, transcript: list = None) -> str:
    """
    Build comprehensive ADVISOR_QUERY with full negotiation context.
    
    Args:
        state: Negotiation state containing item, prices, market_data
        transcript: List of transcript entries (optional)
    
    Returns:
        Formatted ADVISOR_QUERY string with full context
    """
    item = state.get('item') or 'the item being negotiated'
    seller_price = state.get('seller_price')
    target_price = state.get('target_price')
    max_price = state.get('max_price')
    market_data = state.get('market_data', {})
    
    conversation_context = ""
    if transcript:
        if isinstance(transcript, str):
            # Frontend already formatted it
            conversation_context = "Recent conversation:\n" + transcript
        elif isinstance(transcript, list) and len(transcript) > 0:
            # Backend list format
            recent = transcript[-10:] if len(transcript) > 10 else transcript
            conversation_context = "Recent conversation:\n"
            for entry in recent:
                speaker = entry.get('speaker', 'Unknown')
                text = entry.get('text', '')
                conversation_context += f"{speaker}: {text}\n"
            
            if len(transcript) > 10:
                conversation_context += f"\n(+ {len(transcript) - 10} earlier messages)"
    
    market_context = ""
    if market_data:
        price_range = market_data.get('price_range', {})
        if price_range and price_range.get('min') is not None:
            market_context = f"""
Market Research:
- Price range: ₹{price_range['min']:,.0f} - ₹{price_range['max']:,.0f}
- Average: ₹{price_range.get('average', 'N/A'):,.0f}
- Sample: {price_range.get('sample_size', 0)} listings
"""
    
    query = f"""🔔 ADVISOR_QUERY: The USER needs your advice RIGHT NOW 🔔

ITEM: {item}
SELLER PRICE: {f'₹{seller_price:,.0f}' if seller_price else 'Not mentioned'}
USER TARGET: {f'₹{target_price:,.0f}' if target_price else 'Not mentioned'}
USER MAX: {f'₹{max_price:,.0f}' if max_price else 'Not mentioned'}
{market_context}
{conversation_context}

Analyze the situation and provide strategic advice:
1. What information is missing that would help?
2. What does the market data suggest about fair price?
3. What specific tactics should the USER use?

RESPOND WITH AUDIO: Speak your advice out loud. Be specific and actionable."""

    return query


async def trigger_advice_response(live_session, state: dict, transcript: list = None) -> None:
    """
    Trigger AI advice response using the manual activity control sequence.

    Because VAD is DISABLED, Gemini will NOT respond to audio or text unless
    we explicitly signal activity boundaries:

        ActivityStart  →  (text query)  →  ActivityEnd

    This is the ONLY way to get the AI to speak when VAD is off.
    Ref: https://ai.google.dev/api/live#v1alpha.LiveClientActivityStart

    Args:
        live_session: Active Gemini Live API session
        state: Current negotiation state object
        transcript: List of transcript entries for context

    Raises:
        Exception: If any step in the sequence fails
    """
    query = build_advisor_query(state, transcript=transcript)

    logger.info(f"Sending ADVISOR_QUERY to Gemini (length: {len(query)} chars)")
    logger.info(f"Query preview: {query[:200]}...")

    try:
        # The SDK source (live.py) shows activity_start / activity_end are
        # keyword arguments of send_realtime_input(), NOT of send().
        # Each call must have exactly ONE argument.
        #
        #   send_realtime_input(activity_start=...)  → tells Gemini: turn begins
        #   send_realtime_input(text=...)            → the query text
        #   send_realtime_input(activity_end=...)    → tells Gemini: respond now

        await live_session.send_realtime_input(activity_start=types.ActivityStart())
        logger.info("ActivityStart sent")

        await live_session.send_realtime_input(text=query)
        logger.info("ADVISOR_QUERY text sent")

        await live_session.send_realtime_input(activity_end=types.ActivityEnd())
        logger.info("ActivityEnd sent — Gemini should now respond")

    except Exception as e:
        logger.error(f"Activity control sequence failed: {e}")
        raise




async def perform_web_search(query: str) -> dict:
    """
    Perform web search for any query the AI constructs.
    
    This function returns a structured result that will be populated by
    Google Search grounding when the function is called by Gemini.
    
    Args:
        query: Search query constructed by AI based on conversation context
        
    Returns:
        dict: {
            "query": str,
            "results": str,  # Search results summary
            "timestamp": float
        }
    """
    # The actual search is handled by Google Search grounding
    # This function returns the expected format for Gemini
    return {
        "query": query,
        "results": "Will be populated by Google Search grounding",
        "timestamp": time.time()
    }


async def handle_function_call(
    function_name: str,
    args: dict,
    websocket: WebSocket
) -> dict:
    """
    Handle function calls from Gemini.
    
    This function processes function calls triggered by the AI during advice
    generation. Currently supports the web_search function for autonomous
    market research.
    
    Args:
        function_name: Name of the function to call (e.g., "web_search")
        args: Function arguments as a dictionary
        websocket: WebSocket connection for sending notifications to frontend
        
    Returns:
        Function result dictionary to send back to Gemini
        
    Raises:
        Exception: If function execution fails
    """
    if function_name == "web_search":
        query = args.get("query", "")
        
        # Notify frontend that research has started
        await websocket.send_json({
            "type": "RESEARCH_STARTED",
            "payload": {"query": query}
        })
        
        # Perform search (using Google Search grounding)
        result = await perform_web_search(query)
        
        # Notify frontend with results
        await websocket.send_json({
            "type": "RESEARCH_COMPLETE",
            "payload": result
        })
        
        return result
    
    # Unknown function
    return {"error": f"Unknown function: {function_name}"}


async def handle_gemini_text(websocket: WebSocket, session_id: str, text: str) -> None:
    """Handle text responses from Gemini, extracting strategy updates, state updates, and AI responses."""
    STRATEGY_PATTERN = re.compile(r'<strategy>(.*?)</strategy>', re.DOTALL)
    STATE_UPDATE_PATTERN = re.compile(r'<state_update>(.*?)</state_update>', re.DOTALL)
    
    # Extract and send strategy updates
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
    
    # Extract and send state updates (NEW)
    state_updates = STATE_UPDATE_PATTERN.findall(text)
    for state_str in state_updates:
        try:
            state_data = json.loads(state_str)
            logger.info(f"Extracted state update from AI [{session_id}]: {state_data}")
            await websocket.send_json({
                "type": "STATE_UPDATE",
                "payload": state_data
            })
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse state update JSON from session {session_id}: {state_str}")
            
    # Remove all XML tags from text before sending as AI response
    remaining_text = STRATEGY_PATTERN.sub('', text)
    remaining_text = STATE_UPDATE_PATTERN.sub('', remaining_text).strip()
    
    if remaining_text:
        await websocket.send_json({
            "type": "AI_RESPONSE",
            "payload": {
                "response_type": "coaching",
                "text": remaining_text,
                "timestamp": time.time()
            }
        })


async def extract_state_from_transcript(
    websocket: WebSocket, 
    session_id: str, 
    speaker: str, 
    text: str
) -> None:
    """
    You are a silent negotiation advisor listening to a live negotiation.

YOUR ROLE:
- Listen to the conversation between USER and COUNTERPARTY
- Track negotiation details (item, prices, offers, concerns)
- Stay COMPLETELY SILENT unless you see the ADVISOR_QUERY signal

CRITICAL RULES:
1. NEVER respond to the conversation directly
2. NEVER answer questions from USER or COUNTERPARTY
3. ONLY respond when you see: "🔔 ADVISOR_QUERY: USER NEEDS ADVICE NOW 🔔"
4. When you see ADVISOR_QUERY: Provide brief, actionable advice (1-2 sentences)
5. After giving advice: Return to SILENT listening mode

You are an invisible advisor. The negotiating parties cannot hear you unless the user explicitly asks for advice
    """
    state_update = {}
    
    # Extract item names (improved patterns)
    # Look for common product patterns
    item_patterns = [
        # Brand + Model + Variant (iPhone 14 Pro Max, MacBook Pro 2020, etc.)
        r'\b(iPhone\s+\d+(?:\s+Pro)?(?:\s+Max)?)\b',
        r'\b(MacBook\s+(?:Pro|Air)\s*\d*)\b',
        r'\b(iPad\s+(?:Pro|Air|Mini)?\s*\d*)\b',
        r'\b([A-Z][a-z]+\s+[A-Z][a-z]+\s+\d+(?:\s+(?:Pro|Plus|Max|Air|Mini))?)\b',  # Generic: Toyota Camry 2020
        # General pattern: looking at/interested in + product
        r'(?:looking at|interested in|buying|selling|want to buy)\s+(?:a\s+|an\s+|this\s+)?([A-Z][A-Za-z0-9\s]+(?:Pro|Plus|Max|Air|Mini)?)',
    ]
    
    extracted_item = None
    for pattern in item_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            item = match.group(1).strip()
            # Filter out common false positives
            if len(item) > 3 and item not in ['I am', 'You are', 'This is', 'I want', 'Want to']:
                extracted_item = item
                break
    
    # Only include item if we extracted one
    # Frontend will merge intelligently (prefer longer names)
    if extracted_item:
        state_update['item'] = extracted_item
    
    # Extract prices
    # Look for currency symbols or keywords followed by numbers
    price_patterns = [
        r'(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # Indian Rupee
        r'(?:\$|USD)\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # US Dollar
        r'(?:€|EUR)\s*(\d+(?:,\d+)*(?:\.\d+)?)',  # Euro
        r'(?:price|cost|worth|selling for|asking)\s+(?:is\s+)?(?:₹|Rs\.?|\$|€)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                price = float(price_str)
                
                # Determine if this is seller price, target, or max based on context
                if speaker == "counterparty" or "selling" in text.lower() or "asking" in text.lower():
                    state_update['seller_price'] = price
                elif "hoping for" in text.lower() or "target" in text.lower() or "want" in text.lower():
                    state_update['target_price'] = price
                elif "maximum" in text.lower() or "can't go above" in text.lower() or "max" in text.lower():
                    state_update['max_price'] = price
                else:
                    # Default: if user mentions a price, it's likely their target
                    if speaker == "user":
                        state_update['target_price'] = price
                    else:
                        state_update['seller_price'] = price
                        
                break
            except ValueError:
                pass
    
    # Send state update if we extracted anything
    # Include merge_strategy hint for frontend
    if state_update:
        logger.info(f"Auto-extracted state from transcript [{session_id}]: {state_update}")
        await websocket.send_json({
            "type": "STATE_UPDATE",
            "payload": {
                **state_update,
                "_merge_strategy": "smart"  # Hint to frontend to merge intelligently
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
            system_instruction=ADVISOR_SYSTEM_PROMPT,

            # ── VAD ENABLED with barge-in: AI can be interrupted naturally ──
            # Removing the disabled VAD block so Gemini uses its native
            # voice activity detection.  The system prompt keeps the AI
            # SILENT by default — it only responds to the ADVISOR_QUERY trigger.
            # Preemptible voice means the user talking will interrupt the AI.

            # Audio-only responses (no text mode)
            response_modalities=["AUDIO"],

            # Speech configuration — preemptible = barge-in supported
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),

            # Generation config — keep responses short and snappy
            generation_config=types.GenerationConfig(
                temperature=0.8,
                max_output_tokens=300,
                candidate_count=1,
            ),

            # Transcriptions
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),

            # Tools: Google Search grounding
            tools=[
                types.Tool(google_search=types.GoogleSearch())
            ]
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
            if "1007" in str(e) or "invalid frame payload data" in str(e) or "inputaudio" in str(e):
                logger.error(f"1007 error — dropping chunk and continuing [{session_id}]: {e}")
                # Don't re-raise — let next chunk try so the session doesn't die
                return
            logger.error(f"Audio chunk send failed [{session_id}]: {e}")
            raise

    @staticmethod
    async def receive_responses(live_session, websocket: WebSocket, session_id: str, session=None) -> None:
        """
        Receive responses from Gemini Live API.

        IMPORTANT: The receive() iterator ends after each turn_complete.
        We need to call receive() again for each new turn to continue the conversation.
        This is the expected behavior of the Gemini Live API SDK.
        
        Args:
            live_session: Gemini Live API session
            websocket: WebSocket connection to frontend
            session_id: Session ID for logging
            session: NegotiationSession object (optional, for speaker identification)
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
                    
                    # Log every response for debugging
                    logger.info(f"Response #{total_responses}: {type(response).__name__} [{session_id}]")

                    if not response.server_content:
                        logger.info(f"Response #{total_responses}: No server_content [{session_id}]")
                        continue

                    sc = response.server_content
                    
                    # Log what fields are present in server_content
                    has_model_turn = hasattr(sc, 'model_turn') and sc.model_turn
                    has_interrupted = hasattr(sc, 'interrupted') and sc.interrupted
                    has_turn_complete = hasattr(sc, 'turn_complete') and sc.turn_complete
                    has_input_transcript = hasattr(sc, 'input_transcription') and sc.input_transcription
                    has_output_transcript = (hasattr(sc, 'output_transcription') and sc.output_transcription) or (hasattr(sc, 'output_audio_transcription') and sc.output_audio_transcription)
                    
                    logger.info(f"Response #{total_responses}: model_turn={has_model_turn}, interrupted={has_interrupted}, turn_complete={has_turn_complete}, input_transcript={has_input_transcript}, output_transcript={has_output_transcript} [{session_id}]")

                    if sc.interrupted:
                        logger.info(f"Interruption detected [{session_id}]")
                        
                        # Stop forwarding audio if user barges in
                        if getattr(session, 'advisor_active', False):
                            session.advisor_active = False
                            
                        await websocket.send_json({"type": "AUDIO_INTERRUPTED", "payload": {}})
                        continue

                    if sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                                # Only forward audio to frontend if the user requested advice
                                if getattr(session, 'advisor_active', False):
                                    if isinstance(part.inline_data.data, str):
                                        pcm_bytes = base64.b64decode(part.inline_data.data)
                                    else:
                                        pcm_bytes = part.inline_data.data
                                    await websocket.send_bytes(pcm_bytes)
                                # Else drop the audio (prevents AI chatting randomly)
                            elif part.text:
                                await handle_gemini_text(websocket, session_id, part.text)
                            elif hasattr(part, 'function_call') and part.function_call:
                                # Handle function call from Gemini
                                function_name = part.function_call.name
                                function_args = dict(part.function_call.args) if part.function_call.args else {}
                                
                                logger.info(f"Function call received: {function_name}({function_args}) [{session_id}]")
                                
                                try:
                                    # Execute the function
                                    result = await handle_function_call(function_name, function_args, websocket)
                                    
                                    # Send function response back to Gemini
                                    await live_session.send({
                                        "function_response": {
                                            "id": part.function_call.id if hasattr(part.function_call, 'id') else None,
                                            "name": function_name,
                                            "response": result
                                        }
                                    })
                                    
                                    logger.info(f"Function response sent for {function_name} [{session_id}]")
                                except Exception as e:
                                    logger.error(f"Function call failed: {function_name} - {e} [{session_id}]")
                                    # Send error response back to Gemini
                                    await live_session.send({
                                        "function_response": {
                                            "id": part.function_call.id if hasattr(part.function_call, 'id') else None,
                                            "name": function_name,
                                            "response": {"error": str(e)}
                                        }
                                    })

                    if sc.input_transcription and sc.input_transcription.text:
                        # Get speaker label from session (voice fingerprinting) or default to "user"
                        speaker = session.current_speaker if session and hasattr(session, 'current_speaker') else "user"
                        
                        # Create transcript payload
                        transcript_payload = {
                            "speaker": speaker,
                            "text": sc.input_transcription.text,
                            "timestamp": int(time.time() * 1000)
                        }
                        
                        logger.info(f"📝 Transcript received: '{sc.input_transcription.text}' (current_speaker={speaker}) [{session_id}]")
                        
                        # CRITICAL FIX TEMPORARILY DISABLED: Send transcripts immediately
                        # without waiting for speaker identification
                        logger.info(f"✅ Sending transcript immediately (speaker={speaker.upper()}) [{session_id}]")
                        await websocket.send_json({
                            "type": "TRANSCRIPT_UPDATE",
                            "payload": transcript_payload
                        })
                        
                        # User is speaking, so AI is listening
                        await websocket.send_json({
                            "type": "AI_LISTENING",
                            "payload": {}
                        })

                    # Use output_transcription for Vertex AI
                    output_transcription = getattr(sc, 'output_transcription', None) or getattr(sc, 'output_audio_transcription', None)
                    if output_transcription and output_transcription.text:
                        # Only forward text to frontend if the user requested advice
                        if getattr(session, 'advisor_active', False):
                            logger.info(f"✓ AI TRANSCRIPT: '{output_transcription.text}' [{session_id}]")
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
                        
                        # Reset advisor_active to stop listening to microphone when AI is done
                        if getattr(session, 'advisor_active', False):
                            session.advisor_active = False
                            
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

# Export the new functions for manual activity control
__all__ = [
    'GeminiClient',
    'GeminiUnavailableError',
    'build_system_prompt',
    'build_advisor_query',
    'trigger_advice_response',
    'handle_function_call',
    'perform_web_search',
    'open_live_session',
    'send_vision_frame',
    'send_audio_chunk',
    'receive_responses',
    'monitor_session_lifetime',
    'handle_gemini_text',
    'extract_state_from_transcript'
]
