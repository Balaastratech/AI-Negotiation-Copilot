# External Integrations

**Analysis Date:** 2026-03-10

## APIs & External Services

**AI/NLP:**
- **Google Gemini Live API** - Real-time AI negotiation assistant
  - SDK/Client: `google-genai` Python package
  - Primary Model: `gemini-live-2.5-flash-native-audio` (configurable via `GEMINI_MODEL`)
  - Fallback Model: `gemini-2.0-flash-live-001` (configurable via `GEMINI_MODEL_FALLBACK`)
  - Auth: `GEMINI_API_KEY` environment variable
  - Features:
    - Live audio streaming (16kHz PCM input, 24kHz PCM output)
    - Real-time transcription (input and output)
    - Function calling (web_search)
    - Vision capability (JPEG frames)
    - System prompts for negotiation coaching

**Vertex AI (Optional):**
- Enabled via `GOOGLE_GENAI_USE_VERTEXAI` setting
- Requires `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`
- Optional `GOOGLE_APPLICATION_CREDENTIALS` for service account auth

## Data Storage

**Database:**
- Not applicable - Stateless session management
- Session state stored in-memory during active connections

**File Storage:**
- Not applicable - No persistent file storage required

**Caching:**
- Not applicable - No caching layer implemented

## Authentication & Identity

**Auth Provider:**
- None implemented - Open WebSocket endpoint
- Session-based identification via UUID (`session_id`)

## Monitoring & Observability

**Error Tracking:**
- Not detected - No external error tracking service (Sentry, etc.)

**Logs:**
- Python standard `logging` module
- Configurable log level via `LOG_LEVEL` env var (default: INFO)
- Logs output to stdout (Docker-compatible)

## CI/CD & Deployment

**Hosting:**
- Docker containerization
- Dockerfile present at `backend/Dockerfile`

**CI Pipeline:**
- Not detected - No CI service configured

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` - Google AI Studio API key (required)
- `GEMINI_MODEL` - Primary Gemini model (optional, default: `gemini-live-2.5-flash-native-audio`)
- `GEMINI_MODEL_FALLBACK` - Fallback model (optional)
- `CORS_ORIGINS` - Allowed CORS origins (optional, default: `http://localhost:3000`)
- `LOG_LEVEL` - Logging level (optional, default: `INFO`)
- `SESSION_TTL_SECONDS` - Session timeout (optional, default: 3600)

**Optional (Vertex AI):**
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_LOCATION` - GCP region (default: `us-central1`)
- `GOOGLE_GENAI_USE_VERTEXAI` - Enable Vertex AI (boolean)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON

**Secrets location:**
- `backend/.env` file (gitignored, not committed)

## Webhooks & Callbacks

**Incoming:**
- WebSocket endpoint: `ws://host:port/ws`
  - Handles JSON control messages (text frames)
  - Handles binary PCM audio (binary frames)
  - Message types: `START_NEGOTIATION`, `STOP_NEGOTIATION`, `ASK_ADVICE`, `SPEAKER_IDENTIFIED`, `STATE_UPDATE`, `AUDIO_CHUNK`

**Outgoing (to frontend via WebSocket):**
- `CONNECTION_ESTABLISHED` - Session initialization
- `TRANSCRIPT_UPDATE` - Real-time transcription
- `AI_SPEAKING` / `AI_LISTENING` - AI state indicators
- `AI_RESPONSE` - Text/voice responses from AI
- `STRATEGY_UPDATE` - Negotiation strategy recommendations
- `STATE_UPDATE` - Extracted negotiation state (item, prices)
- `RESEARCH_STARTED` / `RESEARCH_COMPLETE` - Web search results
- `AUDIO_INTERRUPTED` - Audio playback interruption
- `AI_DEGRADED` - Connection degradation notification
- `ERROR` - Error notifications
- Binary: Raw PCM audio from Gemini (24kHz)

---

*Integration audit: 2026-03-10*
