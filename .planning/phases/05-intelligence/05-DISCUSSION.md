# Phase 5: Intelligence Integration

## Goal
Connect the live frontend to the live backend with real Gemini negotiation intelligence end-to-end.

## Context & Prerequisites
- **Dependencies:** Phases 2 (Backend Core), 3 (Audio Pipeline), and 4 (Frontend UI) must be complete.
- **Health Check:** The backend health check (`/health`) must be passing locally before proceeding.

## Required Implementations

### 1. Backend Intelligence (`negotiation_engine.py`)
- **Strategy Parser:** Implement parsing of `<strategy>...</strategy>` JSON blocks from Gemini's streaming text.
  - Send successfully parsed blocks to the frontend as `STRATEGY_UPDATE` messages.
  - Send any remaining unstructured text out as `AI_RESPONSE` (coaching) messages.
- **Session Handoff Context (`_build_context_summary`):** 
  - To handle Gemini's strict 10-minute session limit, we must build a context summary summarizing the negotiation (last 10 transcripts and last strategy) to transparently inject into the new session at the 9-minute mark.

### 2. Frontend React Hook (`useNegotiation.ts`)
- **State Management:** This hook becomes the central nervous system connecting `WebSocketClient`, `AudioWorkletManager`, `MediaStreamManager`, and the `NegotiationContext`.
- **Message Routing:**
  - Route binary PCM frames directly to `audioManager.playChunk(buffer)`.
  - Handle all text frames (`ServerMessageType`) according to the `API_SCHEMAS.md` spec (dispatching `SET_CONNECTED`, `SET_CONSENTED`, `SET_NEGOTIATING`, `APPEND_TRANSCRIPT`, `SET_STRATEGY`, etc.).
  - Handle `SESSION_RECONNECTING` silently without blocking the user.
  - Provide a clean API: `connect()`, `grantConsent()`, `startNegotiation()`, `endNegotiation()`, `sendFrame()`.

### 3. End-to-End Integration Testing
- **Manual Verification (Task 5-03):** 
  - Spin up both frontend and backend concurrently.
  - Execute a 10-step manual walkthrough: accept consent -> enable camera -> start negotiation -> speak -> verify transcript -> verify strategy UI -> hear audio back -> end negotiation -> verify outcome summary.

## Identified Risks & Fallbacks (from `CONCERNS.md` & `STATE_MACHINE.md`)
1. **Silent Failures in Strategy Panel:** If Gemini outputs malformed JSON, `JSONDecodeError` should be caught gracefully without crashing the WebSocket session.
2. **Audio Interruptions:** When user barge-in occurs (`sc.interrupted`), the backend will emit `AUDIO_INTERRUPTED` which the frontend hook MUST use to clear the AudioWorklet playback queue.
3. **Graceful AI Degradation:** If the Gemini API goes down entirely (`GeminiUnavailableError`), the `useNegotiation` hook must handle `AI_DEGRADED` to inform the user that vision/voice features are limited.

## Next Steps
Are we ready to proceed to `/gsd:plan-phase 5`?
