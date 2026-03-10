# Architecture

**Analysis Date:** 2026-03-10

## Pattern Overview

**Overall:** Client-Server with WebSocket Real-Time Communication

**Key Characteristics:**
- **Backend**: FastAPI-based async Python server using WebSocket for real-time bidirectional communication
- **Frontend**: Next.js 15 (React 19) with TypeScript, using WebSocket client for real-time AI interaction
- **AI Integration**: Google Gemini Live API (Live 2.5 Flash with native audio) for real-time voice conversation
- **State Machine**: Server-side state machine managing negotiation session lifecycle (IDLE → CONSENTED → ACTIVE → ENDING)

## Layers

### Backend Layers

**API Layer:**
- Location: `backend/app/api/`
- Contains: WebSocket router handling real-time connections
- Depends on: Services layer, Models
- Used by: Frontend WebSocket client
- Key files:
  - `backend/app/api/websocket.py` - WebSocket endpoint (`/ws`) handling message routing

**Services Layer:**
- Location: `backend/app/services/`
- Contains: Business logic for AI communication, negotiation engine, connection management
- Depends on: Models, config
- Used by: API layer
- Key files:
  - `backend/app/services/negotiation_engine.py` - State machine, message validation, routing
  - `backend/app/services/gemini_client.py` - Gemini Live API client (audio, vision, function calls)
  - `backend/app/services/connection_manager.py` - WebSocket connection tracking
  - `backend/app/services/master_prompt.py` - System prompt for AI behavior

**Models Layer:**
- Location: `backend/app/models/`
- Contains: Pydantic models for data validation and serialization
- Depends on: None (pure data)
- Used by: Services, API
- Key files:
  - `backend/app/models/negotiation.py` - NegotiationSession, NegotiationState enum

**Configuration:**
- Location: `backend/app/config.py`
- Contains: Settings using pydantic-settings (env var loading)
- Provides: API keys, model names, CORS settings, logging config

### Frontend Layers

**Page Layer:**
- Location: `frontend/app/`
- Contains: Next.js pages (React components)
- Entry point: `frontend/app/page.tsx` - Main negotiation dashboard

**Component Layer:**
- Location: `frontend/components/`
- Contains: React UI components organized by feature
- Depends on: Hooks layer
- Key directories:
  - `frontend/components/negotiation/` - Negotiation UI components
  - `frontend/components/enrollment/` - Voice enrollment screen

**Hook Layer:**
- Location: `frontend/hooks/`
- Contains: Custom React hooks for state and WebSocket management
- Depends on: Lib layer
- Key files:
  - `frontend/hooks/useNegotiation.ts` - Main WebSocket connection and audio management
  - `frontend/hooks/useNegotiationState.ts` - State management for negotiation data
  - `frontend/hooks/useAskAI.ts` - Button-triggered AI advice
  - `frontend/hooks/useAudioWithSpeakerID.ts` - Audio capture with speaker identification

**Lib Layer:**
- Location: `frontend/lib/`
- Contains: Core utilities, WebSocket client, audio processing
- Key files:
  - `frontend/lib/websocket.ts` - WebSocket client implementation
  - `frontend/lib/audio-worklet-manager.ts` - Audio capture/playback using Web Audio API
  - `frontend/lib/voice-fingerprint.ts` - Voice fingerprinting for speaker identification
  - `frontend/lib/types.ts` - TypeScript type definitions

## Data Flow

**Negotiation Session Flow:**

1. **Connection**: Frontend connects to `ws://host:8000/ws`
   - Backend creates NegotiationSession with UUID
   - Session starts in IDLE state

2. **Consent**: Frontend sends `PRIVACY_CONSENT_GRANTED`
   - Backend transitions to CONSENTED state

3. **Start**: Frontend sends `START_NEGOTIATION` with context
   - Backend opens Gemini Live session
   - Transitions to ACTIVE state
   - Starts async tasks: receive_responses(), monitor_session_lifetime()

4. **Real-Time Communication** (ACTIVE state):
   - **Audio**: Frontend captures PCM audio → sends via WebSocket binary → backend → Gemini Live API
   - **Vision**: Frontend sends base64 frames → backend → Gemini Live API
   - **AI Response**: Gemini Live → backend → WebSocket → Frontend audio playback + transcript

5. **Ask Advice**: Frontend sends `ASK_ADVICE` → backend → triggers Gemini response → streams to frontend

6. **End**: Frontend sends `END_NEGOTIATION`
   - Backend closes Gemini session
   - Sends outcome summary
   - Transitions to IDLE

**State Updates Flow:**
- Gemini extracts negotiation state (item, prices) from transcript
- Backend receives via `<state_update>` XML tags in AI response
- Forwarded to frontend via `STATE_UPDATE` message

## Key Abstractions

**NegotiationSession:**
- Purpose: Server-side session state container
- Examples: `backend/app/models/negotiation.py`
- Pattern: Pydantic BaseModel with runtime-only fields (live_session)

**NegotiationEngine:**
- Purpose: Static methods for message handling and state transitions
- Examples: `backend/app/services/negotiation_engine.py`
- Pattern: Static class with async handlers for each message type

**GeminiClient:**
- Purpose: Wrapper for Google Gemini Live API
- Examples: `backend/app/services/gemini_client.py`
- Pattern: Static methods for session management, audio/video sending, response receiving

**NegotiationWebSocket:**
- Purpose: Frontend WebSocket client abstraction
- Examples: `frontend/lib/websocket.ts`
- Pattern: Class with callbacks for message handling

**AudioWorkletManager:**
- Purpose: Frontend audio capture and playback
- Examples: `frontend/lib/audio-worklet-manager.ts`
- Pattern: Web Audio API + AudioWorklet for low-latency processing

## Entry Points

**Backend Entry:**
- Location: `backend/app/main.py`
- Triggers: uvicorn/fastapi server startup
- Responsibilities: FastAPI app creation, CORS middleware, health endpoints, router inclusion

**Frontend Entry:**
- Location: `frontend/app/page.tsx`
- Triggers: User navigates to root URL
- Responsibilities: Main UI rendering, WebSocket connection, audio management

**WebSocket Endpoint:**
- Location: `backend/app/api/websocket.py`
- Triggers: Frontend connects to `/ws`
- Responsibilities: Session creation, message loop, connection management

## Error Handling

**Strategy:** Graceful degradation with error messages sent via WebSocket

**Patterns:**
- Invalid JSON: Send ERROR message, continue connection
- Invalid state transitions: Send ERROR message, reject operation
- Gemini unavailable: Send GEMINI_UNAVAILABLE error, transition to IDLE
- Audio format errors: Log warning, skip chunk
- WebSocket disconnect: Clean up session, log info

## Cross-Cutting Concerns

**Logging:** Python standard logging (INFO level by default, configurable via LOG_LEVEL)

**Validation:** Pydantic models for request/response validation

**Authentication:** Not implemented (privacy consent only)

**Configuration:** pydantic-settings loading from `.env` file

---

*Architecture analysis: 2026-03-10*
