# Codebase Concerns

**Analysis Date:** 2026-03-07

## Project Status Summary

This is an early-stage project - **AI Negotiation Copilot** built for the Gemini Live Agent Challenge. The codebase contains minimal implementation with extensive planning documentation. The actual source code is skeleton only, with most features not yet implemented.

---

## Critical Gaps (No Implementation)

### No WebSocket Infrastructure

**Issue:** Real-time communication not implemented
- **Files affected:** `backend/app/main.py` (lines 32-34 show placeholder)
- **Impact:** Cannot achieve "Live Agent" category requirement - real-time bidirectional streaming
- **Fix approach:** Implement `backend/app/api/websocket.py` with connection handlers

### No Gemini API Integration

**Issue:** AI client not implemented
- **Files affected:** `backend/app/main.py`, `backend/app/config.py`
- **Impact:** Core value proposition (AI negotiation assistant) non-functional
- **Fix approach:** Implement `backend/app/services/gemini_client.py` with `google-genai` SDK

### No Frontend Components

**Issue:** UI components not created
- **Files affected:** `frontend/app/page.tsx` (only 7 lines - placeholder text)
- **Impact:** No user interface for negotiation
- **Fix approach:** Create components in `frontend/components/negotiation/`

### No Media Streaming

**Issue:** Camera/microphone handling not implemented
- **Impact:** Cannot achieve multimodal "See, Hear, Speak" requirement
- **Fix approach:** Implement `frontend/lib/media-stream.ts` and AudioWorklet

### No Authentication

**Issue:** No auth implemented
- **Files:** WebSocket endpoint, all backend routes
- **Risk:** Unrestricted access to sessions and API
- **Fix approach:** Implement before production deployment

---

## Tech Debt (Current State)

### Minimal Frontend Implementation

**Issue:** Only placeholder code exists
- **Files:** `frontend/app/page.tsx` (7 lines), `frontend/app/layout.tsx` (18 lines)
- **Current content:** Static "ilot" heading onlyAI Negotiation Cop
- **Impact:** No UI functionality, cannot demonstrate features

### Minimal Backend Implementation

**Issue:** Only skeleton exists
- **Files:** `backend/app/main.py` (35 lines), `backend/app/config.py` (14 lines)
- **Current functionality:** Health endpoints only
- **Missing:** WebSocket, Gemini client, session management, API routes

### No Test Infrastructure

**Issue:** Test files not created
- **Directories exist:** `backend/tests/` (empty)
- **Impact:** No way to verify functionality or prevent regressions

---

## Security Concerns

### CORS Allows All Methods

**Issue:** Overly permissive CORS configuration
- **Files:** `backend/app/main.py` (lines 12-18)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **Risk:** While currently uses `localhost:3000` from config, allows all methods/headers
- **Fix approach:** Restrict to specific methods in production

### No Environment Validation

**Issue:** Config requires `GEMINI_API_KEY` but no startup validation
- **Files:** `backend/app/config.py`
- **Risk:** App starts but fails silently when API key missing
- **Fix approach:** Add startup validation in `backend/app/main.py`

### No Secret Management

**Issue:** Sensitive values in `.env.example`
- **Files:** `backend/.env.example`
- **Risk:** Developers may accidentally commit real credentials
- **Mitigation:** Only `.env.example` committed, not `.env`

---

## Configuration Concerns

### Hardcoded Model Versions

**Issue:** Using experimental models without version pinning
- **Files:** `backend/app/config.py` (line 5-6)
```python
GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
```
- **Risk:** Experimental models may break without notice
- **Fix approach:** Pin to specific versions, add validation

### Incomplete Dockerfile

**Issue:** Dockerfile missing production optimizations
- **Files:** `backend/Dockerfile` (17 lines)
- **Missing:** 
  - No multi-stage build
  - No non-root user for production
  - No build arguments for env vars
  - Healthcheck uses curl but curl not installed in python:3.11-slim

### No TypeScript Strict Validation

**Issue:** Frontend tsconfig has strict mode but minimal files to validate
- **Files:** `frontend/tsconfig.json` (strict: true on line 7)
- **Risk:** When components added, strict mode may reveal issues
- **Fix approach:** Ensure all new code passes strict validation

---

## Architectural Concerns

### In-Memory Session Storage (Planned)

**Issue:** Architecture document mentions in-memory sessions
- **Files:** Not yet implemented, but documented in planning
- **Risk:** Sessions lost on restart; no horizontal scaling
- **Fix approach:** Plan Redis integration from start

### Duplicate Model Definitions (Planned)

**Issue:** Similar models in Python and TypeScript
- **Files:** Will affect `backend/app/models/` and `frontend/lib/types.ts`
- **Risk:** Schema drift over time
- **Fix approach:** Consider code generation from Pydantic models

### State Management Complexity (Planned)

**Issue:** Complex negotiation state machine
- **Files:** Will affect frontend state, backend session
- **Risk:** Race conditions in WebSocket messages
- **Fix approach:** Use state machine library, atomic updates

---

## Dependencies at Risk

### google-genai SDK

**Issue:** Rapidly evolving with breaking changes
- **Files:** `backend/requirements.txt` (line 4)
- **Current:** `google-genai>=1.0.0` (no upper bound)
- **Risk:** API changes could break integration
- **Fix approach:** Pin to tested version, verify in staging

### Experimental Gemini Models

**Issue:** Using preview/experimental model versions
- **Files:** `backend/app/config.py`
- **Risk:** Model deprecation, breaking changes
- **Fix approach:** Implement fallback chain, monitor for deprecation

### Next.js 14

**Issue:** Using major version 14 with React 18
- **Files:** `frontend/package.json` (line 12)
- **Current:** `^14.0.0`
- **Risk:** Compatibility issues with React 19 (future)
- **Fix approach:** Monitor upgrade path

---

## Testing Gaps

### No Test Files

**Issue:** `backend/tests/` directory empty
- **Priority:** HIGH
- **Risk:** Cannot verify functionality, breaking changes undetected
- **Fix approach:** Add pytest for backend, vitest for frontend

### No E2E Tests

**Issue:** Manual testing only documented
- **Priority:** HIGH
- **Risk:** Integration issues between frontend/backend
- **Fix approach:** Consider Playwright or Cypress

### No Load Testing

**Issue:** No performance benchmarks
- **Priority:** MEDIUM
- **Risk:** WebSocket scaling issues undetected
- **Fix approach:** Add k6 or similar for load testing

---

## Missing Critical Features (Not Implemented)

| Feature | Status | Impact |
|---------|--------|--------|
| WebSocket Real-time | NOT IMPLEMENTED | Cannot achieve "Live" category |
| Gemini AI Integration | NOT IMPLEMENTED | Core value proposition missing |
| Camera/Mic Access | NOT IMPLEMENTED | No multimodal input |
| Audio Playback | NOT IMPLEMENTED | No AI voice output |
| Authentication | NOT IMPLEMENTED | Security risk in production |
| Rate Limiting | NOT IMPLEMENTED | DoS vulnerability |
| Session Persistence | NOT IMPLEMENTED | Lost on restart |
| Error Handling | MINIMAL | Silent failures |

---

## Scaling Limitations (Future)

### Current Capacity

- **WebSocket:** Cannot handle multiple concurrent connections (not implemented)
- **Sessions:** In-memory only (planned)
- **API:** No rate limiting (not implemented)

### Required for Production

- Redis session store
- Connection pooling for Gemini
- Load balancer
- CDN for frontend

---

## Recommendations

### Immediate (Before Next Phase)

1. **Implement WebSocket infrastructure** - Foundation for all real-time features
2. **Create frontend UI components** - Need working interface for demo
3. **Implement Gemini client** - Core AI functionality
4. **Add basic tests** - Verify each component works

### Before Deployment

1. **Implement authentication** - JWT or session-based
2. **Add rate limiting** - Prevent abuse
3. **Set up Redis** - Session persistence
4. **Configure logging** - For debugging
5. **Health check improvements** - WebSocket-specific checks

### For Hackathon Submission

1. **Working demo** - Must show multimodal features
2. **GCP deployment** - Required proof
3. **Demo video** - Max 4 minutes showing real functionality

---

## Priority Summary

| Priority | Concern | Files |
|----------|---------|-------|
| CRITICAL | WebSocket not implemented | `backend/app/main.py` |
| CRITICAL | Gemini client not implemented | Missing `gemini_client.py` |
| CRITICAL | Frontend has no components | `frontend/app/page.tsx` |
| HIGH | No authentication | All routes |
| HIGH | No tests | `backend/tests/` |
| MEDIUM | CORS too permissive | `backend/app/main.py` |
| MEDIUM | No rate limiting | Not implemented |
| LOW | In-memory sessions (planned) | Will affect scaling |

---

*Concerns audit: 2026-03-07*
