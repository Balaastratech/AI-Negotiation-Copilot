# Gemini Live API Session Architecture

**Status: CRITICAL — Read before writing GeminiClient or NegotiationEngine**
**Last Updated: 2026-03-06**

---

## SDK Correction (Build-Breaker)

The old SDK `google-generativeai` does NOT support the Gemini Live API.

**WRONG (old SDK — do not use):**
```bash
pip install google-generativeai
```
```python
import google.generativeai as genai
genai.GenerativeModel("gemini-2.0-flash-exp")  # Cannot do Live API
```

**CORRECT (new unified SDK):**
```bash
pip install google-genai
```
```python
from google import genai
from google.genai import types
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
```

Update `requirements.txt`:
```
# REMOVE: google-generativeai==0.3.2
google-genai>=1.0.0        # unified SDK with Live API support
```

---

## Model Names

| Purpose | Model String | Notes |
|---|---|---|
| Primary (Live API + native audio) | `gemini-2.5-flash-native-audio-preview-12-2025` | Best for real-time voice |
| Fallback (Live API + text/audio) | `gemini-2.0-flash-live-preview-04-09` | Active preview — replaces deprecated gemini-2.0-flash-live-001 (shut down Dec 9 2025) |
| Text-only fallback (no Live API) | `gemini-2.0-flash` | Use if Live API fails entirely |

**⚠️ `gemini-1.5-flash` and `gemini-1.5-flash-002` do NOT support the Live API. Remove from fallback chain.**

---

## Session Lifecycle

### One Session Per Negotiation

```
Client: START_NEGOTIATION
    ↓
Backend: client.aio.live.connect(model, config)   ← opens Gemini Live WebSocket
    ↓
Backend: store session handle in ConnectionManager.sessions[session_id]['live_session']
    ↓
[Bidirectional streaming for up to 10 minutes]
AUDIO_CHUNK → session.send_realtime_input(audio=blob)
VISION_FRAME → session.send_realtime_input(video=blob)
Gemini responses ← session.receive() async iterator
    ↓
Client: END_NEGOTIATION  OR  9-minute timer fires
    ↓
Backend: session.close()   ← graceful close
    ↓
Backend: compute OUTCOME_SUMMARY
    ↓
Backend: send OUTCOME_SUMMARY to client
    ↓
Session state → IDLE
```

### Session Configuration (Complete)

```python
# backend/app/services/gemini_client.py

from google import genai
from google.genai import types
import os

GEMINI_MODEL_PRIMARY = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_MODEL_FALLBACK = "gemini-2.0-flash-live-preview-04-09"  # replaces gemini-2.0-flash-live-001 (shut down Dec 9 2025)
GEMINI_MODEL_TEXT_ONLY = "gemini-2.0-flash"  # no Live API, last resort

LIVE_SESSION_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO", "TEXT"],

    # Enable Google Search for real-time market price lookup
    tools=[
        types.Tool(google_search=types.GoogleSearch())
    ],

    # Enable transcription of user's speech (appears in TRANSCRIPT_UPDATE)
    input_audio_transcription=types.AudioTranscriptionConfig(),

    # Enable transcription of Gemini's spoken responses
    output_audio_transcription=types.AudioTranscriptionConfig(),

    # System prompt — see SYSTEM_PROMPT.md for full content
    system_instruction=NEGOTIATION_SYSTEM_PROMPT,
)
```

### Opening a Session

```python
# backend/app/services/gemini_client.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def open_live_session(
    api_key: str,
    context: str,
    model: str = GEMINI_MODEL_PRIMARY
):
    """
    Async context manager for a Gemini Live API session.
    
    ✅ CORRECT usage — always use with `async with`:
    
        async with open_live_session(api_key, context) as session:
            await session.send_realtime_input(...)
            async for response in session.receive():
                ...
        # session is automatically closed when the block exits
    
    ❌ WRONG — never call __aenter__() directly:
        session = await client.aio.live.connect(...).__aenter__()  # BROKEN
    
    Falls back to GEMINI_MODEL_FALLBACK if primary fails.
    """
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
            # session closes automatically when caller's async with block exits
    
    except Exception as e:
        logger.warning(f"Primary model {model} failed: {e}. Trying fallback.")
        
        if model != GEMINI_MODEL_FALLBACK:
            async with client.aio.live.connect(
                model=GEMINI_MODEL_FALLBACK, config=config
            ) as session:
                logger.info(f"Gemini Live fallback session opened: {GEMINI_MODEL_FALLBACK}")
                yield session
            return
        
        raise GeminiUnavailableError("All Live API models failed") from e
```

**NegotiationEngine usage pattern:**

```python
# backend/app/services/negotiation_engine.py

async def handle_start(websocket, session_obj, payload, api_key):
    """Open a Gemini Live session and run the negotiation."""
    context = payload.get('context', '')
    
    async with open_live_session(api_key, context) as live_session:
        session_obj.live_session = live_session
        await transition_state(session_obj, NegotiationState.ACTIVE, websocket)
        
        # Run receive loop and lifetime monitor concurrently
        receive_task = asyncio.create_task(
            receive_responses(live_session, websocket, session_obj.session_id)
        )
        monitor_task = asyncio.create_task(
            monitor_session_lifetime(session_obj, websocket, api_key)
        )
        
        # Block until END_NEGOTIATION fires the done_event
        await session_obj.done_event.wait()
        
        receive_task.cancel()
        monitor_task.cancel()
    # session is closed automatically here
```

### Sending Vision Frames

```python
async def send_vision_frame(
    live_session,
    jpeg_base64: str,
    session_id: str
) -> None:
    """
    Send a JPEG camera frame to the active Gemini Live session.
    
    Input: base64-encoded JPEG string from frontend VISION_FRAME message
    """
    try:
        image_bytes = base64.b64decode(jpeg_base64)
        blob = types.Blob(data=image_bytes, mime_type="image/jpeg")
        await live_session.send_realtime_input(video=blob)
    except Exception as e:
        logger.warning(f"Vision frame send failed [{session_id}]: {e}")
        # Non-fatal: continue session without this frame
```

### Sending Audio Chunks

```python
async def send_audio_chunk(
    live_session,
    raw_pcm_bytes: bytes,
    session_id: str
) -> None:
    """
    Send raw PCM audio to Gemini Live session.
    
    Input: Int16 PCM at 16kHz, received as binary WebSocket frame from frontend.
    """
    try:
        blob = types.Blob(data=raw_pcm_bytes, mime_type="audio/pcm;rate=16000")
        await live_session.send_realtime_input(audio=blob)
    except Exception as e:
        logger.warning(f"Audio chunk send failed [{session_id}]: {e}")
        # Non-fatal: skip chunk, continue session
```

### Receiving Gemini Responses

```python
async def receive_responses(
    live_session,
    websocket: WebSocket,
    session_id: str
) -> None:
    """
    Continuous loop receiving Gemini responses and routing to frontend.
    Run as an asyncio Task in parallel with message reception.
    
    Exits when session closes or an unrecoverable error occurs.
    """
    try:
        async for response in live_session.receive():
            
            if not response.server_content:
                continue
            
            sc = response.server_content
            
            # 1. Barge-in signal: user interrupted Gemini's speech
            if sc.interrupted:
                await websocket.send_json({
                    "type": "AUDIO_INTERRUPTED",
                    "payload": {}
                })
                continue
            
            # 2. Audio output: Gemini's spoken response (PCM 24kHz)
            if sc.model_turn:
                for part in sc.model_turn.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                        pcm_bytes = base64.b64decode(part.inline_data.data)
                        await websocket.send_bytes(pcm_bytes)  # binary frame
                    
                    # Text output: strategy JSON from Gemini
                    elif part.text:
                        await handle_gemini_text(websocket, session_id, part.text)
            
            # 3. Input audio transcription (user's speech → text)
            if sc.input_transcription and sc.input_transcription.text:
                await websocket.send_json({
                    "type": "TRANSCRIPT_UPDATE",
                    "payload": {
                        "speaker": "user",
                        "text": sc.input_transcription.text,
                        "timestamp": int(time.time() * 1000)
                    }
                })
            
            # 4. Output audio transcription (Gemini's speech → text)
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
        logger.error(f"Gemini receive loop error [{session_id}]: {e}", exc_info=True)
        await websocket.send_json({
            "type": "AI_DEGRADED",
            "payload": {"message": "AI connection interrupted. Attempting recovery..."}
        })
```

---

## 10-Minute Session Limit Handling

Gemini Live API sessions have a **hard 10-minute limit**. After that, the session is terminated by Google's servers. Without handling this, the app silently dies mid-negotiation.

### Implementation

```python
# backend/app/services/negotiation_engine.py

SESSION_HARD_LIMIT_SECONDS = 600  # 10 minutes
SESSION_HANDOFF_TRIGGER = 540     # 9 minutes — trigger handoff before limit

async def monitor_session_lifetime(
    session: NegotiationSession,
    websocket: WebSocket,
    api_key: str
) -> None:
    """
    Background task monitoring session age.
    At 9 minutes: transparently reconnects Gemini session.
    User experiences no interruption.
    """
    await asyncio.sleep(SESSION_HANDOFF_TRIGGER)
    
    if session.state != NegotiationState.ACTIVE:
        return
    
    logger.info(f"Session handoff triggered [{session.session_id}]")
    
    # 1. Generate context summary from transcript so far
    context_summary = _build_context_summary(session)
    
    # 2. Close old Gemini session
    old_live = session.live_session
    if old_live:
        try:
            await old_live.__aexit__(None, None, None)
        except Exception:
            pass
    
    # 3. Open new Gemini session with context summary injected
    new_live = await open_live_session(
        api_key=api_key,
        context=f"{session.context}\n\nCONTINUATION CONTEXT:\n{context_summary}"
    )
    
    session.live_session = new_live
    
    # 4. Restart receive loop with new session
    asyncio.create_task(
        receive_responses(new_live, websocket, session.session_id)
    )
    
    logger.info(f"Session handoff complete [{session.session_id}]")
    
    # 5. Schedule next handoff
    asyncio.create_task(
        monitor_session_lifetime(session, websocket, api_key)
    )
```

---

## ConnectionManager Session Storage

The `ConnectionManager` must store the Gemini live session handle alongside the WebSocket:

```python
# backend/app/services/connection_manager.py

class ConnectionManager:
    def __init__(self):
        # session_id → { 'ws': WebSocket, 'session': NegotiationSession }
        self.active_connections: dict[str, dict] = {}
    
    async def register(
        self,
        websocket: WebSocket,
        session_id: str,
        session: NegotiationSession
    ) -> None:
        self.active_connections[session_id] = {
            'ws': websocket,
            'session': session,
        }
    
    async def unregister(self, session_id: str) -> None:
        conn = self.active_connections.pop(session_id, None)
        if conn:
            session = conn['session']
            # Close Gemini session if still open
            if session.live_session:
                try:
                    await session.live_session.__aexit__(None, None, None)
                except Exception:
                    pass
    
    def get_session(self, session_id: str) -> NegotiationSession | None:
        conn = self.active_connections.get(session_id)
        return conn['session'] if conn else None
```

---

## Cloud Run Requirements

Cloud Run scales to zero by default. For the hackathon demo, **prevent cold starts**:

```bash
gcloud run deploy ai-negotiation-copilot-backend \
  --image=gcr.io/$PROJECT_ID/ai-negotiation-copilot-backend \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --min-instances=1 \              # ← CRITICAL: prevents cold start during demo
  --max-instances=3 \              # ← enough for concurrent judges
  --memory=1Gi \                   # ← Live API sessions are memory-intensive
  --cpu=2 \
  --timeout=3600 \                 # ← 1hr timeout for long WebSocket sessions
  --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025"
```

Without `--min-instances=1`, a cold start takes 5-15 seconds — the WebSocket connection will fail or timeout during the demo.

---

## GeminiUnavailableError — Graceful Degradation

```python
# backend/app/services/gemini_client.py

class GeminiUnavailableError(Exception):
    """Raised when all Gemini Live API models are unavailable."""
    pass

# In negotiation_engine.py handle_start():
try:
    live_session = await open_live_session(api_key, context)
    session.live_session = live_session
    await transition_state(session, NegotiationState.ACTIVE, websocket)
    
except GeminiUnavailableError:
    # Don't crash — degrade gracefully
    await websocket.send_json({
        "type": "AI_DEGRADED",
        "payload": {
            "message": "AI service is temporarily unavailable. Vision and voice features are limited.",
            "features_available": ["text_strategy"]
        }
    })
    # Still transition to ACTIVE — text-based strategy still works
    await transition_state(session, NegotiationState.ACTIVE, websocket)
```

---

*Gemini session spec: 2026-03-06*
