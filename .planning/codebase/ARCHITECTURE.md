# Architecture

**Analysis Date:** 2026-03-07

## Pattern Overview

**Overall:** Minimal full-stack starter with Next.js frontend and FastAPI backend

**Key Characteristics:**
- Separate frontend (Next.js 14 App Router) and backend (FastAPI Python)
- REST API communication between frontend and backend
- CORS configured to allow frontend dev server
- Health check endpoints implemented
- Google Gemini AI integration planned

## Layers

### Frontend (Next.js)

**Purpose:** React-based UI for negotiation assistance
- **Location:** `frontend/app/`
- **Contains:** Page components and layouts only
- **Depends on:** Browser APIs, TailwindCSS
- **Used by:** End users via browser
- **Status:** Minimal starter - only landing page implemented

**Missing components:**
- `components/negotiation/` - Not yet created
- `components/ui/` - Not yet created  
- `components/providers/` - Not yet created
- `lib/` - Not yet created
- `hooks/` - Not yet created

### Backend API Layer

**Purpose:** HTTP endpoints and request handling
- **Location:** `backend/app/`
- **Contains:** `main.py` (entry point), `config.py` (settings)
- **Depends on:** FastAPI, Pydantic
- **Used by:** Frontend HTTP clients

**Implemented:**
- FastAPI app initialization in `backend/app/main.py`
- CORS middleware configuration
- Health check endpoints (`/api/health`, `/health`)
- Configuration via Pydantic Settings

**Missing:**
- `backend/app/api/` directory with route handlers
- `backend/app/services/` with business logic
- `backend/app/models/` with data schemas
- WebSocket endpoint

## Data Flow

**Current API Communication:**

1. Frontend (browser) → HTTP GET to `localhost:3000` (Next.js)
2. Backend runs on `localhost:8080` (FastAPI)
3. Health check at `/health` returns `{"status": "healthy"}`

**Planned Flow (not implemented):**
```
Client → WebSocket → Backend → Gemini Live API → Response → Client UI
```

## Key Abstractions

**Frontend Configuration:**
- Purpose: Next.js configuration and environment setup
- Files: `frontend/next.config.js`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`
- Pattern: Standard Next.js 14 App Router config with path alias `@/*`

**Backend Configuration:**
- Purpose: Centralized settings using Pydantic
- Files: `backend/app/config.py`
- Pattern: Pydantic Settings with environment variable support

```python
# backend/app/config.py
class Config(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    SESSION_TTL_SECONDS: int = 3600
```

## Entry Points

### Frontend Entry

- **Location:** `frontend/app/page.tsx`
- **Triggers:** Browser navigates to `/`
- **Responsibilities:** Render main page with "AI Negotiation Copilot" heading
- **Current implementation:** Minimal stub

```tsx
// frontend/app/page.tsx
export default function Home() {
  return (
    <main>
      <h1>AI Negotiation Copilot</h1>
    </main>
  )
}
```

### Frontend Layout

- **Location:** `frontend/app/layout.tsx`
- **Responsibilities:** HTML shell, metadata, global styles

### Backend Entry

- **Location:** `backend/app/main.py`
- **Triggers:** `uvicorn app.main:app --host 0.0.0.0 --port 8080`
- **Responsibilities:** Initialize FastAPI app, configure CORS, health endpoints
- **Configured in:** `backend/Dockerfile`

## Error Handling

**Strategy:** Not fully implemented - placeholder code only

**Patterns:**
- Backend: Returns JSON error responses via FastAPI
- Frontend: Not yet implemented (minimal stub)

## Cross-Cutting Concerns

**Logging:** Python standard logging in backend
```python
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)
```

**Validation:** Pydantic models for config validation
**Authentication:** Not implemented - placeholder for future
**CORS:** Configured to allow `http://localhost:3000`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

*Architecture analysis: 2026-03-07*
