# Codebase Concerns

**Analysis Date:** 2026-03-10

## Tech Debt

### Duplicate State Management Hooks
- **Issue:** Two overlapping state management systems exist: `useNegotiation` (line 4 in `frontend/app/page.tsx`) and `useNegotiationState` (line 5 in `frontend/app/page.tsx`). Both track similar data (transcript, prices, strategy) but in different ways.
- **Files:** `frontend/hooks/useNegotiation.ts`, `frontend/hooks/useNegotiationState.ts`, `frontend/app/page.tsx`
- **Impact:** Confusing data flow, potential synchronization issues between two state sources
- **Fix approach:** Consolidate into single state management approach, remove redundant state

### Mock Data Controls Still in Production Code
- **Issue:** Dev-only mock data loading button exists in production build. Located in `frontend/app/negotiate/page.tsx` (lines 77-87).
- **Files:** `frontend/app/negotiate/page.tsx`
- **Impact:** Accidental clicking could reset state or cause unexpected behavior in production
- **Fix approach:** Wrap in `process.env.NODE_ENV === 'development'` condition or remove entirely

### Debug Console Logs in Production
- **Issue:** Multiple `console.log` statements scattered throughout frontend hooks for debugging purposes
- **Files:** `frontend/hooks/useNegotiation.ts` (lines 135, 146, 154, 206, 244, 252, 279), `frontend/hooks/useAskAI.ts` (lines 46, 52, 86)
- **Impact:** Exposes internal state to browser console, potential performance overhead
- **Fix approach:** Remove console.log statements or replace with proper logging service

### Unused Import - Handshake Icon
- **Issue:** `StrategyPanel.tsx` imports `Handshake` from `lucide-react` (line 3) but the icon is never used in the component
- **Files:** `frontend/components/negotiation/StrategyPanel.tsx`
- **Impact:** Causes TypeScript build error: `Module '"lucide-react"' has no exported member 'Handshake'`
- **Fix approach:** Remove unused import

### Hardcoded Voice Enrollment Bypass
- **Issue:** Voice enrollment is hardcoded to `true`, skipping the enrollment screen entirely
- **Files:** `frontend/app/page.tsx` (line 45)
- **Impact:** Voice fingerprinting features are disabled, speaker identification won't work
- **Fix approach:** Restore proper enrollment flow or make configurable

## Known Bugs

### AI Not Responding to ADVISOR_QUERY (Critical)
- **Symptoms:** When user clicks "Ask AI" button, the AI receives the query but does not generate any audio response. Logs show `model_turn=None`
- **Files:** `backend/app/services/gemini_client.py`, `backend/app/services/master_prompt.py`
- **Trigger:** Click "Ask AI" button during active negotiation session
- **Workaround:** Multiple fix attempts documented in `WHY_AI_NOT_RESPONDING.md` and `AI_RESPONSE_FIX.md`. Current approach tries 3 different send methods as fallbacks

### Audio Format Errors
- **Symptoms:** Backend logs show `AUDIO FORMAT ERROR: Odd byte count` or `invalid frame payload data` errors
- **Files:** `backend/app/services/gemini_client.py` (lines 452-455, 676-681)
- **Trigger:** Sending audio chunks to Gemini API
- **Workaround:** Validation added for odd byte count detection, but root cause (frontend sending corrupted audio) not fully addressed

### TypeScript Build Error
- **Symptoms:** Frontend fails to build due to missing `Handshake` export from lucide-react
- **Files:** `frontend/components/negotiation/StrategyPanel.tsx`
- **Trigger:** Running `npm run build` or TypeScript compilation
- **Workaround:** Remove the unused `Handshake` import

### Potential None Reference Error in Session Handoff
- **Symptoms:** LSP reports `"__aexit__" is not a known attribute of "None"` in negotiation_engine.py
- **Files:** `backend/app/services/negotiation_engine.py` (line 150)
- **Trigger:** Session handoff when `old_live` is None
- **Workaround:** Add null check before calling `__aexit__`

## Security Considerations

### WebSocket Connection Security
- **Risk:** WebSocket connection uses `ws://` protocol by default without explicit TLS enforcement
- **Files:** `frontend/hooks/useNegotiation.ts`, `frontend/app/page.tsx` (line 67)
- **Current mitigation:** Falls back to `wss://` if on HTTPS
- **Recommendations:** Enforce WSS in production, add connection validation

### No Authentication on WebSocket
- **Risk:** No authentication token required to connect to WebSocket endpoint
- **Files:** `backend/app/api/websocket.py`
- **Current mitigation:** None detected
- **Recommendations:** Add JWT or API key validation on WebSocket connection

### Hardcoded Session Context
- **Issue:** Default negotiation context is hardcoded: "I am buying a used laptop at a market. The seller is asking $500."
- **Files:** `frontend/app/page.tsx` (line 150)
- **Impact:** All sessions start with same context, potential data leakage if this changes
- **Recommendations:** Make configurable or remove hardcoded values

## Performance Bottlenecks

### Session Hard Limit (10 Minutes)
- **Problem:** Sessions are limited to 600 seconds (10 minutes) with automatic handoff at 540 seconds
- **Files:** `backend/app/services/gemini_client.py` (lines 24-25)
- **Cause:** Hardcoded limits for API usage control
- **Improvement path:** Make configurable, add session resume capability, or increase limits for production use

### Audio Processing Without Batching
- **Problem:** Each audio chunk is sent individually to Gemini API without batching
- **Files:** `backend/app/services/gemini_client.py` (lines 447-480)
- **Cause:** Sequential processing of audio chunks
- **Improvement path:** Implement audio buffering and batch sending for better throughput

### Rolling Transcript Window
- **Problem:** 90-second rolling window in `useNegotiationState.ts` may lose important context
- **Files:** `frontend/hooks/useNegotiationState.ts` (lines 101-106)
- **Impact:** AI may not have full conversation history for context
- **Improvement path:** Implement smarter windowing that preserves key price discussions

## Fragile Areas

### Complex Gemini API Integration
- **Files:** `backend/app/services/gemini_client.py` (753 lines)
- **Why fragile:** Multiple fallback mechanisms, version-specific API calls, complex state machine for handling responses
- **Safe modification:** Test any changes with both primary and fallback models
- **Test coverage:** No unit tests found for this module

### WebSocket Message Routing
- **Files:** `backend/app/api/websocket.py`, `backend/app/services/negotiation_engine.py`
- **Why fragile:** Complex routing of different message types (audio, text, vision) with different validation and handling paths
- **Safe modification:** Add comprehensive logging for any new message types
- **Test coverage:** No integration tests for WebSocket message handling

### Frontend State Synchronization
- **Files:** `frontend/app/page.tsx`, `frontend/hooks/useNegotiation.ts`, `frontend/hooks/useNegotiationState.ts`
- **Why fragile:** Two state sources that need to stay in sync but may diverge
- **Safe modification:** Consolidate to single state management before adding new features
- **Test coverage:** Limited - only `useNegotiationState.test.ts` found

## Scaling Limits

### WebSocket Connection Limits
- **Current capacity:** Unknown - depends on uvicorn worker count
- **Limit:** Single backend instance can handle limited concurrent connections
- **Scaling path:** Implement Redis-based connection manager for horizontal scaling

### Gemini API Rate Limits
- **Current capacity:** Not documented in codebase
- **Limit:** Google API quotas
- **Scaling path:** Implement request queuing and caching for repeated queries

### Session State Memory
- **Current capacity:** In-memory session storage
- **Limit:** Each session holds transcript, strategy history
- **Scaling path:** Move to Redis for session storage, implement cleanup

## Dependencies at Risk

### Gemini Live API SDK
- **Risk:** Uses `v1alpha` API version which may change without notice
- **Files:** `backend/app/services/gemini_client.py` (line 363)
- **Impact:** Breaking changes could stop all AI functionality
- **Migration plan:** Monitor Google's API changelog, test with preview releases

### Lucide React Icons
- **Risk:** Importing non-existent icon `Handshake` causes build failure
- **Files:** `frontend/components/negotiation/StrategyPanel.tsx`
- **Impact:** Frontend cannot build
- **Migration plan:** Use valid icon names from lucide-react library

## Missing Critical Features

### Error Boundaries
- **Problem:** No React error boundaries to catch rendering errors
- **Impact:** Single component error can crash entire app

### Retry Logic for WebSocket
- **Problem:** No automatic reconnection if WebSocket drops
- **Impact:** User must manually refresh page on connection loss

### Input Validation
- **Problem:** Limited validation on WebSocket messages
- **Impact:** Malformed messages could crash session

### Testing Infrastructure
- **Problem:** Only one test file exists (`frontend/tests/example.test.ts`)
- **Impact:** No regression protection

## Test Coverage Gaps

### Backend Services
- **What's not tested:** All backend Python services
- **Files:** `backend/app/services/*.py`, `backend/app/api/*.py`
- **Risk:** Bugs in core AI logic go undetected
- **Priority:** High

### Frontend Hooks (Except useNegotiationState)
- **What's not tested:** `useNegotiation.ts`, `useAskAI.ts`, `useAudioWithSpeakerID.ts`
- **Files:** `frontend/hooks/`
- **Risk:** State management bugs could cause data loss
- **Priority:** High

### WebSocket Message Handling
- **What's not tested:** Message parsing, routing, and validation
- **Risk:** Security vulnerabilities from unvalidated input
- **Priority:** High

---

*Concerns audit: 2026-03-10*
