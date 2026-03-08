# External Integrations

**Analysis Date:** 2026-03-07

## APIs & External Services

**AI & Machine Learning:**
- **Google Gemini API** - Core AI engine for negotiation assistance
  - SDK: `google-genai` Python package
  - Models: 
    - Primary: `gemini-2.5-flash-native-audio-preview-12-2025`
    - Fallback: `gemini-2.0-flash-live-preview-04-09`
  - Features: Audio streaming, vision analysis, text generation
  - Auth: `GEMINI_API_KEY` environment variable
  - Configuration: `backend/app/config.py`

**Browser APIs (Planned/Not Yet Implemented):**
- MediaDevices.getUserMedia - Camera and microphone access
- Web Audio API - Audio processing and visualization
- WebSocket - Real-time communication

## Data Storage

**Databases:**
- None currently configured

**File Storage:**
- Local filesystem only (development)

**Caching:**
- None currently configured

## Authentication & Identity

**Auth Provider:**
- None currently implemented
- Privacy consent system not yet implemented

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Backend: Python logging module
- Configuration: `LOG_LEVEL` environment variable (default: INFO)
- Implementation: `backend/app/main.py` - `logging.basicConfig(level=settings.LOG_LEVEL)`

**Health Checks:**
- Endpoint: `/health` - Health status
- Endpoint: `/api/health` - API health status
- Returns: `{"status": "healthy"}`

## CI/CD & Deployment

**Hosting:**
- Docker - Backend containerization
- Next.js - Frontend (development)

**CI Pipeline:**
- None explicitly configured

**Docker Configuration:**
- `backend/Dockerfile` - Python 3.11-slim image
- Runs on port 8080
- Healthcheck: `curl -f http://localhost:8080/health`

## Environment Configuration

**Required env vars (Backend):**
- `GEMINI_API_KEY` - Gemini API authentication key
- `GEMINI_MODEL` - Model version
- `GEMINI_MODEL_FALLBACK` - Fallback model
- `CORS_ORIGINS` - Allowed origins
- `LOG_LEVEL` - Logging level
- `SESSION_TTL_SECONDS` - Session timeout

**Example (.env.example):**
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
GEMINI_MODEL_FALLBACK=gemini-2.0-flash-live-preview-04-09
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
SESSION_TTL_SECONDS=3600
```

**Secrets location:**
- `.env` files (local development)
- Never committed to version control

## Webhooks & Callbacks

**Incoming:**
- None - Client initiates all connections

**Outgoing:**
- None currently configured

## Integration Summary

| Service | Purpose | SDK/Client | Auth Method |
|---------|---------|-----------|-------------|
| Gemini API | AI negotiation assistance | `google-genai` | API Key |
| Docker | Containerization | Native | N/A |

---

*Integration audit: 2026-03-07*
