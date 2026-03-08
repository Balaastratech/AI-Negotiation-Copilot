# Negotiation State Machine

**Status: CRITICAL — All backend WebSocket message handlers MUST check state before processing**
**Last Updated: 2026-03-06**

---

## State Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │                   IDLE                          │
                    │  - No active session                            │
                    │  - No Gemini connection                         │
                    └────────────────────┬────────────────────────────┘
                                         │ PRIVACY_CONSENT_GRANTED
                                         ↓
                    ┌─────────────────────────────────────────────────┐
                    │                 CONSENTED                       │
                    │  - Consent recorded                             │
                    │  - Waiting for user to start negotiation        │
                    └────────────────────┬────────────────────────────┘
                                         │ START_NEGOTIATION
                                         ↓
                    ┌─────────────────────────────────────────────────┐
                    │                  ACTIVE                         │
                    │  - Gemini Live session open                     │
                    │  - Audio/vision streaming live                  │
                    │  - Strategy updates flowing                     │
                    └────────────────────┬────────────────────────────┘
                                         │ END_NEGOTIATION
                                         │ or session_timeout
                                         │ or client_disconnect
                                         ↓
                    ┌─────────────────────────────────────────────────┐
                    │                  ENDING                         │
                    │  - Gemini session closing                       │
                    │  - Outcome being computed                       │
                    │  - Awaiting OUTCOME_SUMMARY send                │
                    └────────────────────┬────────────────────────────┘
                                         │ OUTCOME_SUMMARY sent
                                         ↓
                                       IDLE
```

---

## State Definitions

### `IDLE`
- **Entry condition:** Initial connection OR after `OUTCOME_SUMMARY` sent
- **Gemini session:** None
- **Accepts:** `PRIVACY_CONSENT_GRANTED`
- **Rejects all other messages with:**
  ```json
  { "type": "ERROR", "payload": { "code": "NOT_CONSENTED", "message": "Please accept privacy terms first." } }
  ```

### `CONSENTED`
- **Entry condition:** `PRIVACY_CONSENT_GRANTED` received and recorded
- **Gemini session:** None
- **Accepts:** `START_NEGOTIATION`
- **Rejects with:**
  ```json
  { "type": "ERROR", "payload": { "code": "NOT_STARTED", "message": "Start a negotiation session first." } }
  ```

### `ACTIVE`
- **Entry condition:** `START_NEGOTIATION` received, Gemini session successfully opened
- **Gemini session:** OPEN — persistent `client.aio.live.connect()` session
- **Accepts:** `VISION_FRAME`, `AUDIO_CHUNK`, `END_NEGOTIATION`
- **Rejects with:**
  ```json
  { "type": "ERROR", "payload": { "code": "ALREADY_ACTIVE", "message": "Session already in progress." } }
  ```
- **Special:** At 9 minutes into session, triggers automatic Gemini session handoff (see GEMINI_SESSION.md)

### `ENDING`
- **Entry condition:** `END_NEGOTIATION` received OR session timeout
- **Gemini session:** Closing
- **Accepts:** Nothing (all messages queued and dropped)
- **Sends:** `OUTCOME_SUMMARY` before transitioning to IDLE
- **Max duration:** 10 seconds — if outcome not computed, send partial summary

---

## Python Implementation

### Session State Model

```python
# backend/app/models/negotiation.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel
import time

class NegotiationState(str, Enum):
    IDLE = "IDLE"
    CONSENTED = "CONSENTED"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"

class NegotiationSession(BaseModel):
    session_id: str
    state: NegotiationState = NegotiationState.IDLE
    consent_version: Optional[str] = None
    consent_mode: Optional[str] = None  # "live" or "roleplay"
    started_at: Optional[float] = None  # unix timestamp
    context: str = ""                   # negotiation context string
    live_session: Optional[object] = None  # Gemini live session handle (not serialized)
    
    # Outcome tracking
    initial_price: Optional[float] = None
    final_price: Optional[float] = None
    transcript: list[dict] = []
    strategy_history: list[dict] = []

    class Config:
        arbitrary_types_allowed = True  # required for live_session handle
```

### State Machine Enforcer

```python
# backend/app/services/negotiation_engine.py

import logging
from app.models.negotiation import NegotiationSession, NegotiationState
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Valid messages per state
VALID_MESSAGES: dict[NegotiationState, list[str]] = {
    NegotiationState.IDLE:      ["PRIVACY_CONSENT_GRANTED"],
    NegotiationState.CONSENTED: ["START_NEGOTIATION"],
    NegotiationState.ACTIVE:    ["VISION_FRAME", "AUDIO_CHUNK", "END_NEGOTIATION"],
    NegotiationState.ENDING:    [],  # nothing accepted while computing outcome
}

ERROR_CODES: dict[NegotiationState, dict] = {
    NegotiationState.IDLE:      {"code": "NOT_CONSENTED",   "message": "Please accept privacy terms first."},
    NegotiationState.CONSENTED: {"code": "NOT_STARTED",     "message": "Start a negotiation session first."},
    NegotiationState.ACTIVE:    {"code": "ALREADY_ACTIVE",  "message": "Session already in progress."},
    NegotiationState.ENDING:    {"code": "SESSION_ENDING",  "message": "Session is ending, please wait."},
}

async def validate_message(
    websocket: WebSocket,
    session: NegotiationSession,
    message_type: str
) -> bool:
    """
    Check if message_type is valid for current session state.
    Sends ERROR response if invalid.
    Returns True if valid, False if rejected.
    """
    allowed = VALID_MESSAGES.get(session.state, [])
    
    if message_type not in allowed:
        error = ERROR_CODES.get(session.state, {"code": "INVALID_STATE", "message": "Invalid operation."})
        await websocket.send_json({"type": "ERROR", "payload": error})
        logger.warning(
            f"Rejected {message_type} in state {session.state} "
            f"[session={session.session_id}]"
        )
        return False
    
    return True

async def transition_state(
    session: NegotiationSession,
    new_state: NegotiationState,
    websocket: WebSocket
) -> None:
    """Log and apply a state transition."""
    old_state = session.state
    session.state = new_state
    logger.info(f"State: {old_state} → {new_state} [session={session.session_id}]")
```

### WebSocket Handler Pattern

```python
# backend/app/api/websocket.py

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    session = NegotiationSession(session_id=session_id)
    
    await websocket.accept()
    await connection_manager.register(websocket, session_id, session)
    
    await websocket.send_json({
        "type": "CONNECTION_ESTABLISHED",
        "payload": {"session_id": session_id}
    })
    
    try:
        while True:
            # Distinguish binary (audio) from text (control) frames
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                # Binary frame = audio chunk
                if not await validate_message(websocket, session, "AUDIO_CHUNK"):
                    continue
                await handle_audio_chunk(websocket, session, message["bytes"])
                
            elif "text" in message and message["text"]:
                # Text frame = JSON control message
                data = json.loads(message["text"])
                msg_type = data.get("type", "UNKNOWN")
                
                if not await validate_message(websocket, session, msg_type):
                    continue
                
                await route_message(websocket, session, msg_type, data.get("payload", {}))
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected [session={session_id}]")
        await cleanup_session(session)
    
    except Exception as e:
        logger.error(f"WebSocket error [session={session_id}]: {e}", exc_info=True)
        await websocket.send_json({
            "type": "ERROR",
            "payload": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
        })
    
    finally:
        await connection_manager.unregister(session_id)
```

---

## Message Routing Table

| Message Type | Valid In State | Handler Function | State Transition |
|---|---|---|---|
| `PRIVACY_CONSENT_GRANTED` | `IDLE` | `handle_consent()` | `IDLE → CONSENTED` |
| `START_NEGOTIATION` | `CONSENTED` | `handle_start()` | `CONSENTED → ACTIVE` |
| `VISION_FRAME` (JSON) | `ACTIVE` | `handle_vision_frame()` | None |
| `AUDIO_CHUNK` (binary) | `ACTIVE` | `handle_audio_chunk()` | None |
| `END_NEGOTIATION` | `ACTIVE` | `handle_end()` | `ACTIVE → ENDING → IDLE` |

---

## Error Response Catalog

All error responses follow this exact schema:

```json
{
  "type": "ERROR",
  "payload": {
    "code": "ERROR_CODE",
    "message": "Human-readable message shown to user."
  }
}
```

| Code | Trigger | User Message |
|---|---|---|
| `NOT_CONSENTED` | Any message before consent | "Please accept privacy terms first." |
| `NOT_STARTED` | Media/strategy before start | "Start a negotiation session first." |
| `ALREADY_ACTIVE` | Second START_NEGOTIATION | "Session already in progress." |
| `SESSION_ENDING` | Message during ENDING | "Session is ending, please wait." |
| `PAYLOAD_TOO_LARGE` | Message > 10MB | "Message too large." |
| `INVALID_MESSAGE` | Malformed JSON | "Invalid message format." |
| `GEMINI_UNAVAILABLE` | All Gemini models fail | "AI service unavailable. Please try again." |
| `INTERNAL_ERROR` | Unhandled exception | "An unexpected error occurred." |
| `SESSION_TIMEOUT` | 10-min Gemini limit | "Session expired. Please start a new negotiation." |

---

## Fallback Behaviors (Define These Explicitly for Agent)

```python
FALLBACK_BEHAVIORS = {
    # Gemini session disconnects mid-negotiation
    # DECISION: Auto-reconnect silently (Option A, locked 2026-03-06)
    # 1. Send SESSION_RECONNECTING to frontend immediately (non-blocking indicator)
    # 2. Rebuild context summary from transcript so far
    # 3. Open new Gemini session with context injected
    # 4. Send SESSION_STARTED when new session is live
    # 5. If all 3 attempts fail → send AI_DEGRADED, continue text-only mode
    "gemini_session_disconnect":
        "send SESSION_RECONNECTING, attempt reconnect with saved context (max 3 tries), "
        "send SESSION_STARTED on success, emit AI_DEGRADED if all fail, continue in text-only mode",
    
    # Vision analysis returns low confidence
    "vision_low_confidence":
        "set vision_active=False in session, "
        "continue audio-only, do not show error to user",
    
    # Audio chunk arrives too large (>1MB)
    "audio_chunk_oversized":
        "split into 4096-sample chunks, send sequentially, log warning",
    
    # Gemini 10-minute session limit approaching
    "gemini_session_near_limit":
        "at 9m00s: save context summary, close session, open new session, "
        "inject context summary as first message, user sees no interruption",
    
    # Web search tool unavailable in Gemini
    "google_search_unavailable":
        "continue with model knowledge only, "
        "strategy panel shows 'Using AI knowledge (live prices unavailable)'",
    
    # Client WebSocket drops mid-session
    "client_disconnect":
        "keep session in ACTIVE state for 60s, "
        "allow reconnect with same session_id via ?resume=session_id query param",
    
    # OUTCOME_SUMMARY computation takes > 10s
    "outcome_timeout":
        "send partial summary with available data, "
        "include disclaimer 'Analysis may be incomplete'",
}
```

---

*State machine spec: 2026-03-06*
