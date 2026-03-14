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
from app.services.master_prompt import  ADVISOR_SYSTEM_PROMPT
from app.services.response_validator import ResponseValidator

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


def build_advisor_query(state: dict, transcript: list = None, user_query: str = "Command.") -> str:
    """
    Builds a persona-reinforcing query for the COMMAND CENTER AI.

    This function frames the user's request as a tactical command, explicitly
    reminding the AI of its core persona and instructions from the
    ADVISOR_SYSTEM_PROMPT to prevent persona-breaking conversational drift.
    
    Args:
        state: The current negotiation state (included for compatibility).
        transcript: A recent transcript snippet (included for compatibility).
        user_query: The live query from the user.

    Returns:
        A formatted string to be sent to the Gemini Live API.
    """
    reminder = "You are a ruthless tactical commander. Adhere strictly to the persona and instructions defined in your ADVISOR_SYSTEM_PROMPT."

    # Frame the query as a direct order for tactical advice.
    query_block = (
        "[TACTICAL REQUEST]\n"
        f"INSTRUCTION: {reminder}\n"
        "Analyze all available context from the ongoing conversation and give me a direct, decisive command. Do not ask questions or offer options.\n"
        f"My explicit query is: \"{user_query}\"\n"
        "[/TACTICAL REQUEST]"
    )
    return query_block


async def trigger_advice_response(live_session, state: dict, transcript: list = None) -> None:
    """
    Triggers an AI advice response by sending the query via the standard chat channel.

    This method uses session.send() to transmit the text query, which correctly
    associates it with the system prompt and treats it as a standard conversational
    turn, ensuring the model's persona and instructions are respected.

    Args:
        live_session: Active Gemini Live API session
        state: Current negotiation state object
        transcript: List of transcript entries for context

    Raises:
        Exception: If the send operation fails
    """
    query = build_advisor_query(state, transcript=transcript)

    logger.info(f"Sending ADVISOR_QUERY to Gemini (length: {len(query)} chars)")
    logger.info(f"Query preview: {query[:200]}...")

    try:
        # Send text via the standard turn-based chat channel, NOT the realtime media channel.
        # This properly attaches the query to the system prompt context.
        await live_session.send(input=query, end_of_turn=True)
        logger.info("ADVISOR_QUERY sent successfully — Gemini should now respond")

    except Exception as e:
        logger.error(f"Failed to send text query: {e}")
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


# Global dictionary to accumulate text per session for the current turn
_session_text_accumulators = {}

async def handle_gemini_text(websocket: WebSocket, session_id: str, text: str) -> None:
    """Handle text responses from Gemini, extracting strategy/state updates and accumulating coaching text."""
    logger.debug("Handling Gemini text", extra={"session_id": session_id, "text": text})
    global _session_text_accumulators
    
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
    
    # Extract and send state updates
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
            
    # Remove all XML tags from text
    remaining_text = STRATEGY_PATTERN.sub('', text)
    remaining_text = STATE_UPDATE_PATTERN.sub('', remaining_text).strip()
    
    # Accumulate the remaining text for this session's turn
    if remaining_text:
        if session_id not in _session_text_accumulators:
            _session_text_accumulators[session_id] = ""
        # Ensure there's a space between chunks if they don't already have one
        if _session_text_accumulators[session_id] and not _session_text_accumulators[session_id].endswith(' ') and not remaining_text.startswith(' '):
            _session_text_accumulators[session_id] += " "
        _session_text_accumulators[session_id] += remaining_text


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
        
        # Combine the base system prompt with the user-provided context
        full_system_instruction = f"{ADVISOR_SYSTEM_PROMPT}\n\nNEGOTIATION CONTEXT:\n{context}"

        logger.info(
            "Opening Gemini Live session with system instruction",
            extra={"full_system_instruction": full_system_instruction},
        )
 
        config = types.LiveConnectConfig(
            system_instruction=types.Content(
                #role="system", # Ensure Vertex prioritizes this
                parts=[types.Part.from_text(text=full_system_instruction)] # Safe serialization
            ),

            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=True
                )
            ),

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

            # Generation config — optimized for constraint following
            generation_config=types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
                candidate_count=1,
                top_p=0.8,
                top_k=20,
            ),

            # Transcriptions
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),

            # FIX: Removed GoogleSearch tool - Listener Agent does the market research
            # and injects market_data into Live AI via LISTENER_INTEL messages.
            # This prevents duplicate research and ensures specific item research.
            # tools=[
            #     types.Tool(google_search=types.GoogleSearch())
            # ],

            # Context window compression — prevents overflow in 30+ min negotiations (Risk 8)
            # Sliding window triggers at 100K tokens, silently compresses older context.
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow(),
                trigger_tokens=100_000,
            ),
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
                    logger.info(
                        "Received response from Live AI",
                        extra={
                            "session_id": session_id,
                            "response_type": type(response).__name__,
                            "server_content": str(response.server_content),
                        },
                    )

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
                    
                    logger.info(f"DBG: GeminiClient Response #{total_responses}: model_turn={has_model_turn}, interrupted={has_interrupted}, turn_complete={has_turn_complete}, input_transcript={has_input_transcript}, output_transcript={has_output_transcript} [{session_id}]")

                    if sc.interrupted:
                        logger.info(f"AI Interrupted by user [session={session_id}]")
                        if session:
                            session.ai_is_speaking = False
                            # On barge-in: only reset user_addressing_ai if copilot is NOT active.
                            # When copilot is active, the interruption is normal barge-in during
                            # monitoring mode — do not close the audio gate.
                            if not getattr(session, 'copilot_active', False):
                                session.user_addressing_ai = False
                            
                            # Flush any pending injections that arrived while AI was speaking
                            from app.services.negotiation_engine import NegotiationEngine
                            await NegotiationEngine.flush_pending_injections(session)

                        await websocket.send_json({"type": "AUDIO_INTERRUPTED", "payload": {}})
                        continue

                    if sc.model_turn:
                        # AI has started speaking. Set the speaker state to prevent the
                        # Listener from analyzing the AI's own audio output.
                        if session:
                            session.ai_is_speaking = True
                            session.current_speaker = "ai"

                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                                if isinstance(part.inline_data.data, str):
                                    pcm_bytes = base64.b64decode(part.inline_data.data)
                                else:
                                    pcm_bytes = part.inline_data.data
                                await websocket.send_bytes(pcm_bytes)
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
                        
                        if session:
                            session.last_user_transcript = sc.input_transcription.text

                        # Send user transcripts immediately for separate display
                        # This ensures each question appears separately in the UI
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

                    # Handle AI output transcription separately (outside input_transcription block)
                    output_transcription = getattr(sc, 'output_transcription', None) or getattr(sc, 'output_audio_transcription', None)
                    if output_transcription and output_transcription.text:
                        ai_text = output_transcription.text
                        response_mode = getattr(session, 'response_mode', 'command')
                        
                        logger.info(f"[DEBUG] AI response chunk received. Mode: {response_mode}, Text: '{ai_text[:50]}...'")

                        # Always accumulate the full response for potential validation
                        if not hasattr(session, 'current_ai_response'):
                            session.current_ai_response = ""
                        session.current_ai_response += " " + ai_text if session.current_ai_response else ai_text

                        # AI_TRANSCRIPTION_DISPLAY disabled

                        # Set AI speaking state
                        if not getattr(session, 'ai_is_speaking', False):
                            session.ai_is_speaking = True
                            await websocket.send_json({"type": "AI_SPEAKING", "payload": {}})
                        
                        session.current_speaker = "ai"
                        session.speaker_last_updated = time.time()


                    # Check for turn_complete - this signals the end of this receive() iteration
                    if hasattr(sc, 'turn_complete') and sc.turn_complete:
                        logger.info(f"AI turn complete [session={session_id}]")
                        
                        # VALIDATE AI RESPONSE BEFORE COMPLETING TURN
                        # Skip validation if response_mode is "advice"
                        response_mode = getattr(session, 'response_mode', 'command')
                        
                        if session and hasattr(session, 'current_ai_response') and session.current_ai_response:
                            full_response = session.current_ai_response.strip()
                            
                            # Only validate in "command" mode, skip for "advice" mode
                            if response_mode == "command":
                                validation_result = ResponseValidator.validate_response(full_response)
                                
                                if not validation_result["valid"]:
                                    logger.warning(
                                        f"AI response violated rules: {validation_result['violations']} [{session_id}]"
                                    )
                                    logger.warning(f"Violating response: '{full_response}' [{session_id}]")
                                    
                                    # Send correction if critical violations
                                    if ResponseValidator.should_send_correction(validation_result["violations"]):
                                        correction = validation_result["correction_prompt"]
                                        logger.info(f"Sending correction to AI: '{correction}' [{session_id}]")
                                        
                                        # Send correction immediately
                                        try:
                                            await live_session.send(input=correction, end_of_turn=True)
                                            
                                            # Notify frontend about correction
                                            await websocket.send_json({
                                                "type": "AI_CORRECTION_SENT",
                                                "payload": {
                                                    "violations": validation_result["violations"],
                                                    "correction": correction
                                                }
                                            })
                                        except Exception as e:
                                            logger.error(f"Failed to send correction: {e} [{session_id}]")
                                else:
                                    logger.info(f"✅ AI response validated successfully [{session_id}]")
                                    # Send the validated response to the frontend
                                    await websocket.send_json({
                                        "type": "TRANSCRIPT_UPDATE",
                                        "payload": {
                                            "speaker": "ai",
                                            "text": full_response,
                                            "timestamp": int(time.time() * 1000)
                                        }
                                    })
                            else: # This is advice mode
                                logger.info(f"Advice mode - skipping validation, sending transcript [{session_id}]")
                                await websocket.send_json({
                                    "type": "TRANSCRIPT_UPDATE",
                                    "payload": {
                                        "speaker": "ai",
                                        "text": full_response,
                                        "timestamp": int(time.time() * 1000)
                                    }
                                })
                            
                            # Clear accumulated response
                            session.current_ai_response = ""

                        if session:
                            session.ai_is_speaking = False
                            # Reset speaker to last known human so Listener can resume analysis
                            if session.current_speaker == "ai":
                                session.current_speaker = "user" # Default back to user
                            
                            # After any AI turn completes, always discard pending injections.
                            # Flushing them immediately would trigger a second proactive AI turn
                            # causing the double-response bug. The listener cycle (10s) will
                            # inject fresh context on the next pass instead.
                            session.direct_query_in_flight = False
                            if session.pending_injections:
                                count = len(session.pending_injections)
                                session.pending_injections.clear()
                                logger.info(
                                    f"Cleared {count} pending injections after turn complete "
                                    f"[session={session_id}]"
                                )

                        # Turn is over, AI is now listening
                        await websocket.send_json({"type": "AI_LISTENING", "payload": {}})

                        # Mark turn as cleanly completed before breaking
                        turn_complete_received = True
                        # Break from this turn's receive() loop. The outer while True
                        # will immediately call receive() again for the next turn.
                        break

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

                # Turn completed successfully, increment counter and loop will call receive() again for next turn
                turn_count += 1
                logger.debug(f"Turn #{turn_count} complete. Ready for turn #{turn_count + 1}, calling receive() again [{session_id}]")
                await asyncio.sleep(0.01)  # Brief pause before next receive() call

            except asyncio.CancelledError:
                logger.info(f"Receive loop cancelled after {turn_count} turns [{session_id}]")
                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)

                # Check if this is the 1007 Chirp 3 codec error (native audio model state mismatch).
                # After the model generates audio output, subsequent raw PCM input causes:
                #   "audio/x-raw-tokens requires ContentChunk.tokens.token_ids to be set"
                # Recovery: auto-reconnect opens a fresh session that accepts PCM again.
                if "1007" in error_msg or "invalid frame payload data" in error_msg or "inputaudio" in error_msg:
                    logger.warning(
                        f"1007 codec error [{session_id}] — triggering auto-reconnect: {error_msg}"
                    )
                    if session:
                        from app.services.negotiation_engine import NegotiationEngine
                        asyncio.create_task(
                            NegotiationEngine._reconnect_live_session(session, websocket)
                        )
                    else:
                        try:
                            await websocket.send_json({
                                "type": "AI_DEGRADED",
                                "payload": {"message": "AI connection error (1007). Please refresh."}
                            })
                        except Exception:
                            pass
                else:
                    logger.error(
                        f"Receive loop error after {turn_count} turns [{session_id}]: "
                        f"{error_type}: {error_msg}", exc_info=True
                    )
                    try:
                        await websocket.send_json({
                            "type": "AI_DEGRADED",
                            "payload": {"message": f"AI connection error: {error_msg}"}
                        })
                    except Exception:
                        pass
                break  # Exit this receive loop — reconnect (or degraded) handled above

    @staticmethod
    async def keepalive_ping(session: NegotiationSession) -> None:
        """
        Send periodic keepalive pings to prevent Gemini Live WebSocket timeout.
        
        The Gemini Live WebSocket has a ~30 second keepalive timeout. If no messages
        are sent within that window, the connection closes with error 1011.
        
        This function sends a minimal message every 20 seconds to keep the connection alive.
        """
        while session.live_session and session.state == NegotiationState.ACTIVE:
            try:
                await asyncio.sleep(20)  # Ping every 20 seconds (before 30s timeout)
                
                if session.live_session and session.state == NegotiationState.ACTIVE:
                    # Send a minimal keepalive message (empty text with turn_complete=False)
                    async with session.gemini_send_lock:
                        await session.live_session.send_client_content(
                            turns=types.Content(
                                role="user",
                                parts=[types.Part(text="")],
                            ),
                            turn_complete=False,
                        )
                    logger.debug(f"Keepalive ping sent [session={session.session_id}]")
            except Exception as e:
                logger.warning(f"Keepalive ping failed (session may be closing): {e}")
                break

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
            # D5: Use the async context manager correctly
            async with open_live_session(
                api_key=api_key,
                context=f"{session.context}\n\nCONTINUATION CONTEXT:\n{context_summary}"
            ) as new_live:
                session.live_session = new_live
                
                # D5 — Preserve copilot state across handoff
                if session.copilot_active and session.listener_agent:
                    last_ctx = session.listener_agent.last_context
                    if last_ctx:
                        # Logic to format and inject priming text
                        # This reuses the logic from the plan, ensuring consistency
                        from app.services.negotiation_engine import NegotiationEngine
                        await NegotiationEngine._inject_context_to_live_ai(session, last_ctx, [])
                        logger.info(f"Session handoff: primed new session with listener context [{session.session_id}]")

                asyncio.create_task(receive_responses(new_live, websocket, session.session_id, session))
                logger.info(f"Session handoff complete [{session.session_id}]")
                # Relaunch the monitor for the *next* handoff
                asyncio.create_task(monitor_session_lifetime(session, websocket, api_key))
        except Exception as e:
            logger.error(f"Failed to hand off session [{session.session_id}]: {e}")

open_live_session = GeminiClient.open_live_session
send_vision_frame = GeminiClient.send_vision_frame
send_audio_chunk = GeminiClient.send_audio_chunk
receive_responses = GeminiClient.receive_responses
monitor_session_lifetime = GeminiClient.monitor_session_lifetime
keepalive_ping = GeminiClient.keepalive_ping

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
    'keepalive_ping',
    'handle_gemini_text',
    'extract_state_from_transcript'
]
