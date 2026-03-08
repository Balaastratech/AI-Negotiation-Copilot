# Phase 2: Backend Core - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Working FastAPI WebSocket server with full Gemini Live API session management. Includes Pydantic models, ConnectionManager, GeminiClient, NegotiationEngine, and WebSocket endpoint.

</domain>

<decisions>
## Implementation Decisions

### SDK Selection
- google-genai (NOT google-generativeai - old SDK doesn't support Live API)
- Specified in: `.planning/codebase/GEMINI_SESSION.md`

### Model Configuration
- Primary: gemini-2.5-flash-native-audio-preview-12-2025
- Fallback: gemini-2.0-flash-live-preview-04-09
- Specified in: `.planning/codebase/GEMINI_SESSION.md`

### State Machine
- IDLE → CONSENTED → ACTIVE → ENDING → IDLE
- All transitions and error codes defined in STATE_MACHINE.md
- Specified in: `.planning/codebase/STATE_MACHINE.md`

### Message Schemas
- All client→server and server→client message formats exact
- Binary frame handling for PCM audio
- Specified in: `.planning/codebase/API_SCHEMAS.md`

### Session Configuration
- response_modalities: ["AUDIO", "TEXT"]
- Google Search tool enabled for market price lookup
- Session timeout: 9 minutes (with handoff)
- Specified in: `.planning/codebase/GEMINI_SESSION.md`

### Claude's Discretion
- Exact logging format and levels
- Error message wording details
- Development vs production behavior differences

</decisions>

<specifics>
## Specific Ideas

No specific requirements — all implementation details specified in:
- `.planning/codebase/GEMINI_SESSION.md` (SDK, models, session config)
- `.planning/codebase/STATE_MACHINE.md` (state transitions, error codes)
- `.planning/codebase/API_SCHEMAS.md` (message payloads)

</specifics>

<a
## Existing Code Insights

### Reusable Assets
- backend/app/main.py — FastAPI app with CORS middleware
- backend/app/config.py — pydantic-settings Config class

### Established Patterns
- Python: pydantic for models, pydantic-settings for config
- FastAPI: async/await, WebSocket handling patterns
- Logging: using Python logging module

### Integration Points
- WebSocket endpoint at /ws
- Health endpoints at /health and /api/health
- CORS configured for localhost:3000

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-backend-core*
*Context gathered: 2026-03-07*
