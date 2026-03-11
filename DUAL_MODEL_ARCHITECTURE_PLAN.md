# Dual-Model AI Negotiation Copilot — Full Implementation Plan

## What We're Building

A **continuous AI negotiation coach** with two models working together:

- **Listener Agent** (Gemini 2.5 Flash, standard API): runs in the background every 10 seconds with 15-second overlapping windows, transcribes and extracts structured negotiation context (item, prices, tactics) from the audio stream
- **Live Advisor** (Gemini Live, native audio): stays connected as a natural conversational partner — listens, handles barge-in/interruptions, and receives enriched context injections from the listener

The "Ask AI" button is the **primary trigger** for advice — proactive speaking is disabled for demo stability (can be enabled post-hackathon).

---

## Architecture Diagram

```
MICROPHONE
  │
  ├──(raw PCM)──────────────────────────────────────────────────────┐
  │                                                                  ▼
  │                                                     ┌─────────────────────────┐
  │                                          every 10s  │   LISTENER AGENT        │
  │                                          ◄──────────│   gemini-2.5-flash      │
  │                                                     │   (standard API)        │
  │                                                     │                         │
  │                                                     │ input: 15s audio window │
  │                                                     │   (5s overlap)          │
  │                                                     │   base64-encoded PCM    │
  │                                                     │ output: {               │
  │                                                     │   item, seller_price,   │
  │                                                     │   transcript_segment,   │
  │                                                     │   key_moments, tactics  │
  │                                                     │ }                       │
  │                                                     └───────────┬─────────────┘
  │                                                     inject context (no response)
  │                                                     via shared lock
  │                                                                 │
  ▼                                                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        LIVE ADVISOR AGENT                                │
│                   gemini-live-2.5-flash-native-audio                     │
│                                                                          │
│  Config:                                                                 │
│  - VAD enabled (natural conversation, barge-in supported)                │
│  - proactive_audio = False (button-triggered only for demo stability)   │
│  - output: AUDIO only                                                    │
│  - input/output transcription enabled (for frontend display)             │
│  - Shared gemini_send_lock with listener to prevent race conditions     │
│                                                                          │
│  Behaviours:                                                             │
│  - Stays silent until "Ask AI" button pressed                            │
│  - Receives context from listener before responding                      │
│  - Stops immediately when user speaks (barge-in)                         │
│  - Responds with 2-3 sentence tactical advice                            │
│  - Returns to silent listening after response                            │
└──────────────────────────────────────────────────────────────────────────┘
  │
  ▼  (AI audio response)
SPEAKER → User hears advice
```

---

## Backend — New Files

### 1. `backend/app/services/audio_buffer.py`
A thread-safe rolling audio buffer that holds the last 90 seconds of raw PCM audio.

```python
from collections import deque
from typing import List

class AudioBuffer:
    def __init__(self, duration_seconds=90, sample_rate=16000):
        self.max_samples = duration_seconds * sample_rate
        self.buffer = deque(maxlen=self.max_samples // 1600)  # 100ms chunks
        
    def push(self, raw_pcm: bytes):
        """Add new audio chunk"""
        self.buffer.append(raw_pcm)
    
    def get_last_n_seconds(self, n: int) -> bytes:
        """Get last N seconds for advisor"""
        num_chunks = (n * 16000) // 1600
        return b''.join(list(self.buffer)[-num_chunks:])
    
    def get_overlapping_window(self, window_seconds=15) -> bytes:
        """Get 15-second window for listener (called every 10s = 5s overlap)"""
        num_chunks = (window_seconds * 16000) // 1600
        return b''.join(list(self.buffer)[-num_chunks:])
    
    def get_all(self) -> bytes:
        return b''.join(self.buffer)
    
    def clear(self):
        self.buffer.clear()
```

### 2. `backend/app/services/listener_agent.py`
Background task that periodically sends audio to Gemini Flash for transcription and context extraction.

```python
import asyncio
import base64
import json  # CRITICAL: needed for json.dumps()
import logging
from collections import deque
from google import genai

logger = logging.getLogger(__name__)

# LISTENER_PROMPT - used in _analyze_audio_chunk
LISTENER_PROMPT = """You are a silent negotiation analyst.

LISTEN to all audio and extract:
1. Speaker labels: [USER] or [SELLER]
2. Item being negotiated
3. Prices mentioned (seller's ask, user's offer)
4. Leverage points (condition issues, market data, urgency)
5. Key moments (concessions, objections, tactics)

Output as JSON:
{
  "item": "iPhone 16 Pro",
  "seller_price": 50000,
  "user_offer": 40000,
  "transcript_segment": "[USER] How much? [SELLER] ₹50,000",
  "leverage_points": ["Market avg ₹42k", "Visible scratch"],
  "key_moments": ["Seller said 'maybe' - shows flexibility"]
}

NEVER generate audio responses. Only output structured JSON."""

class ListenerAgent:
    INTERVAL_SECONDS = 10
    WINDOW_SECONDS = 15  # 15s window with 10s stride = 5s overlap
    FLASH_MODEL = "gemini-2.5-flash"  # Better at structured extraction
    
    def __init__(self, audio_buffer, gemini_send_lock, api_key: str, websocket):
        self.audio_buffer = audio_buffer
        self.gemini_send_lock = gemini_send_lock  # CRITICAL: shared lock
        self.websocket = websocket  # CRITICAL: needed to send CONTEXT_UPDATE to frontend
        self.accumulated_transcript = deque(maxlen=20)  # Cap at 20 entries
        
        # CRITICAL: Use new google-genai SDK (not old google.generativeai)
        self.client = genai.Client(api_key=api_key)
        
        self.running = False
        self.task = None
    
    async def start(self, live_session):
        self.live_session = live_session
        self.running = True
        self.task = asyncio.create_task(self._run_loop())
    
    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
    
    async def _run_loop(self):
        """Main loop with error handling - one failure shouldn't kill the listener"""
        while self.running:
            await asyncio.sleep(self.INTERVAL_SECONDS)
            try:
                audio_window = self.audio_buffer.get_overlapping_window(self.WINDOW_SECONDS)
                if audio_window:
                    await self._analyze_audio_chunk(audio_window)
            except Exception as e:
                logger.warning(f"[ListenerAgent] Cycle failed, skipping: {e}")
                # Don't re-raise - loop continues
    
    async def _analyze_audio_chunk(self, audio_bytes: bytes):
        """Send audio to Flash API with base64 encoding"""
        audio_b64 = base64.b64encode(audio_bytes).decode()
        
        # CRITICAL: Call Flash WITHOUT holding the lock (can take 2-5 seconds)
        # Holding lock here would freeze audio streaming to Live session
        
        # CRITICAL: Both audio and prompt must be in SINGLE content object (not two)
        # Two separate content objects = alternating turns, Flash gets confused
        response = await self.client.aio.models.generate_content(
            model=self.FLASH_MODEL,
            contents=[
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/pcm;rate=16000",  # CRITICAL: include rate
                                "data": audio_b64
                            }
                        },
                        {"text": LISTENER_PROMPT}  # Same content object, second part
                    ]
                }
            ]
        )
        
        context = self._parse_context(response.text)
        
        # CRITICAL: Store context in accumulated_transcript for Ask AI button
        if context:
            self.accumulated_transcript.append(context)
        
        await self._inject_context(context)
    
    def _parse_context(self, response_text: str) -> dict:
        """Parse JSON context from Flash response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except Exception as e:
            logger.warning(f"[ListenerAgent] Failed to parse context: {e}")
            return {}
    
    async def _inject_context(self, context: dict):
        """Inject context into Live session AND update frontend UI"""
        if not context:
            return
        
        context_msg = f"<context>{json.dumps(context)}</context>"
        
        # 1. Update Live advisor (silent, no response)
        # CRITICAL: Only hold lock for the fast inject (milliseconds, not seconds)
        async with self.gemini_send_lock:
            # Use system role update - documented and won't trigger response
            await self.live_session.send_client_content(
                turns=[{"role": "system", "parts": [{"text": context_msg}]}],
                turn_complete=False
            )
        
        # 2. Update frontend UI context card
        # CRITICAL: Without this, the context card never updates during demo
        await self.websocket.send_json({
            "type": "CONTEXT_UPDATE",
            "payload": context
        })
```

## Backend — Modified Files

### 3. `backend/app/models/negotiation.py`
Add fields for the listener agent and audio buffer:
```python
from collections import deque

class NegotiationSession:
    audio_buffer: AudioBuffer
    listener_agent: ListenerAgent
    gemini_send_lock: asyncio.Lock  # CRITICAL: shared lock
    negotiation_context: dict
    # Note: accumulated_transcript now lives in ListenerAgent (capped at 20)
```

### 4. `backend/app/services/gemini_client.py`
**LiveConnectConfig Updates:**
```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=ADVISOR_PROMPT,
    
    # VAD enabled for natural conversation
    # automatic_activity_detection defaults to ENABLED - keep it
    
    # CRITICAL: Disable proactive audio for demo stability
    # proactive_audio defaults to False - keep it that way
    
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            preemptible_voice_config=types.PreemptibleVoiceConfig(
                voice_name="Aoede"
            )
        )
    ),
    
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
)
```

**Function Updates:**

```python
async def receive_responses(session_id: str):
    """
    Receive and broadcast Gemini's audio + transcription responses.
    """
    session = sessions[session_id]
    live_session = session['live_session']
    
    async for response in live_session.receive():
        if response.server_content:
            # Broadcast audio to frontend
            if response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.inline_data:
                        await broadcast_to_frontend(session_id, {
                            'type': 'AUDIO_RESPONSE',
                            'audio': part.inline_data.data
                        })
        
        # Broadcast transcription if available
        if response.output_audio_transcription:
            await broadcast_to_frontend(session_id, {
                'type': 'TRANSCRIPT_UPDATE',
                'text': response.output_audio_transcription.text,
                'speaker': 'AI'
            })
```

**Note:** The `trigger_advice_response()` function has been removed to avoid duplication. Use `handle_ask_ai_button()` in `negotiation_engine.py` instead, as it has direct access to the session dict.


### 5. `backend/app/services/negotiation_engine.py`
```python
import asyncio
import json  # CRITICAL: needed for json.dumps() in handle_ask_ai_button

async def handle_start_negotiation(session_id: str, context: dict, api_key: str, websocket):
    # Initialize shared lock FIRST
    gemini_send_lock = asyncio.Lock()
    
    # Initialize audio buffer
    audio_buffer = AudioBuffer(duration_seconds=90)
    
    # Start Live session
    live_session = await start_live_session(config, gemini_send_lock)
    
    # Start listener agent with shared lock, API key, and websocket
    listener_agent = ListenerAgent(audio_buffer, gemini_send_lock, api_key, websocket)
    await listener_agent.start(live_session)
    
    # Store in session
    sessions[session_id] = {
        'audio_buffer': audio_buffer,
        'listener_agent': listener_agent,
        'live_session': live_session,
        'gemini_send_lock': gemini_send_lock,
        'context': context,  # Store initial context (item, target price)
        'websocket': websocket  # Store for other handlers
    }

async def handle_audio_chunk(session_id: str, audio_chunk: bytes):
    session = sessions[session_id]
    
    # Feed to buffer (listener reads from it every 10s)
    session['audio_buffer'].push(audio_chunk)
    
    # CRITICAL: Acquire lock before sending to Live session
    async with session['gemini_send_lock']:
        await session['live_session'].send_realtime_input(audio=audio_chunk)

async def handle_ask_ai_button(session_id: str):
    """Handle user clicking 'Ask AI' button - trigger advice response"""
    session = sessions[session_id]
    
    # Get listener's latest context
    listener_context = session['listener_agent'].accumulated_transcript
    initial_context = session['context']
    
    # Build focused query with all available context
    query = f"""User needs advice NOW.

Initial context:
- Item: {initial_context.get('item', 'unknown')}
- Target price: {initial_context.get('target_price', 'unknown')}

Recent conversation (last 20 segments):
{json.dumps(list(listener_context), indent=2)}

Provide 2-3 sentence tactical advice for the user's next move."""
    
    # CRITICAL: Acquire lock before sending
    async with session['gemini_send_lock']:
        await session['live_session'].send_client_content(
            turns=[{"role": "user", "parts": [{"text": query}]}],
            turn_complete=True  # This triggers the response
        )

async def handle_end_negotiation(session_id: str):
    session = sessions[session_id]
    
    # Stop listener
    await session['listener_agent'].stop()
    
    # Close Live session
    await session['live_session'].close()
    
    # Clear buffer
    session['audio_buffer'].clear()
```

### 6. `backend/app/services/master_prompt.py`
System prompt for the button-triggered advisor role.

```python
ADVISOR_PROMPT = """You are a tactical negotiation advisor.

You receive:
- Context from listener AI (item, prices, leverage, transcript)
- Last 30 seconds of audio
- Trigger signal when user clicks "Ask AI" button

RESPONSE FORMAT (2-3 sentences max):
"[What to say]. [Why/leverage]. [Fallback]."

Example: "Offer ₹40,000 - market shows ₹38-45k range. If they refuse, ask about warranty to justify their price."

Stay concise and actionable. Focus on the next tactical move.
"""
```

**Note:** `LISTENER_PROMPT` is now defined in `listener_agent.py` where it's actually used, not here.

## Frontend — Modified Files

### 7. `frontend/app/page.tsx`
- Keep a minimal pre-session form with 2 fields:
  - Item you're negotiating for
  - Your target price
- This gives the listener initial context to work with

### 8. `frontend/hooks/useNegotiation.ts`
- Handle new `CONTEXT_UPDATE` message from the Listener Agent
- Update `negotiationState` so the UI's Context Card updates automatically
- Display listener's extracted context in real-time

---

## Critical Implementation Notes

### ⚠️ MUST-HAVE for Hackathon Demo

1. **Shared Lock Usage**: Lock ONLY for fast operations (send_client_content), NOT for slow Flash API calls
2. **Audio Encoding**: Listener sends base64-encoded PCM with `audio/pcm;rate=16000` MIME type (rate parameter is critical)
3. **Overlapping Windows**: 15-second window every 10 seconds (5s overlap) prevents transcript gaps
4. **Transcript Cap**: Keep only last 20 entries to prevent context bloat
5. **Proactive Audio OFF**: Keep `proactive_audio=False` for demo stability
6. **Model Choice**: Use `gemini-2.5-flash` for listener (better at structured extraction)
7. **Context Injection**: Use system role updates (not user role) to avoid triggering responses
8. **Error Handling**: Wrap listener loop in try/except - one Flash failure shouldn't kill the entire listener
9. **SDK Consistency**: Use new `google-genai` SDK throughout (not old `google.generativeai`)

## Critical Implementation Notes

### ⚠️ MUST-HAVE for Hackathon Demo

1. **Lock Usage Pattern**: Lock ONLY for fast operations (send_client_content), NOT for slow Flash API calls
   - ❌ BAD: Hold lock during 2-5 second Flash API call → freezes audio streaming
   - ✅ GOOD: Call Flash without lock, then acquire lock only for fast inject
   
2. **Audio Encoding**: Listener sends base64-encoded PCM with `audio/pcm;rate=16000` MIME type
   - ❌ BAD: `audio/pcm` → Flash misinterprets sample rate, garbage transcriptions
   - ✅ GOOD: `audio/pcm;rate=16000` → Correct transcription
   
3. **Context Injection Method**: Use system role updates (not user role) to avoid triggering responses
   - ❌ BAD: `{"role": "user", ...}` with `turn_complete=False` → May trigger response
   - ✅ GOOD: `{"role": "system", ...}` with `turn_complete=False` → Documented, safe
   
4. **SDK Consistency**: Use new `google-genai` SDK throughout (not old `google.generativeai`)
   - ❌ BAD: Mix old and new SDK → Import conflicts, auth issues
   - ✅ GOOD: Use `from google import genai` and `genai.Client()` everywhere
   
5. **Error Handling**: Wrap listener loop in try/except
   - ❌ BAD: One Flash 429/500 error kills listener forever
   - ✅ GOOD: Log error, skip cycle, continue loop

6. **Multimodal Content Structure**: Audio and prompt must be in SINGLE content object
   - ❌ BAD: Two separate content objects → Flash treats as alternating turns, gets confused
   - ✅ GOOD: One content object with two parts (audio + text)

7. **Frontend Updates**: Listener must send CONTEXT_UPDATE to websocket
   - ❌ BAD: Only inject to Live session → Context card never updates
   - ✅ GOOD: Inject to both Live session AND websocket → UI updates in real-time

8. **Overlapping Windows**: 15-second window every 10 seconds (5s overlap) prevents transcript gaps
9. **Transcript Cap**: Keep only last 20 entries to prevent context bloat
10. **Proactive Audio OFF**: Keep `proactive_audio=False` for demo stability
11. **Model Choice**: Use `gemini-2.5-flash` for listener (better at structured extraction)

### 🎯 Build Priority for March 16

**MUST BUILD:**
- ✅ AudioBuffer with overlapping window method
- ✅ ListenerAgent with base64 encoding + shared lock
- ✅ Shared `gemini_send_lock` in negotiation engine
- ✅ Context injection without triggering response
- ✅ Button-triggered advice with context
- ✅ Minimal pre-session form (item + target price)

**CUT FOR NOW:**
- ❌ Proactive audio (too risky for demo)
- ❌ Affective dialog (unverifiable in 4-min video)
- ❌ Intelligent triggering logic (button-only is safer)
- ❌ Session resumption (15-min limit is fine)
