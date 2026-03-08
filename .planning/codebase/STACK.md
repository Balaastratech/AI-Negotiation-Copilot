# Technology Stack

**Analysis Date:** 2026-03-07

## Languages

**Primary:**
- Python 3.11 - Backend API (FastAPI)
- TypeScript - Frontend (Next.js)

**Secondary:**
- CSS - Styling (Tailwind CSS)

## Runtime

**Environment:**
- Node.js 18+ (inferred from @types/node ^20.0.0)
- Python 3.11

**Package Managers:**
- npm - Frontend
- pip - Backend
- Lockfiles: `package-lock.json` (present)

## Frameworks

**Core Backend:**
- FastAPI 0.109.0+ - Web framework
- Uvicorn 0.27.0+ - ASGI server

**Core Frontend:**
- Next.js 14.0.0 - React framework (App Router)
- React 18.2.0 - UI library

**Testing:**
- Not detected

**Build/Dev:**
- Tailwind CSS 3.4.0 - Styling
- PostCSS 8.4.32 - CSS processing
- Autoprefixer 10.4.16 - Vendor prefixes
- TypeScript 5.0.0 - Type safety

## Key Dependencies

**Critical (Backend):**
- `fastapi` 0.109.0+ - Web framework
- `uvicorn[standard]` 0.27.0+ - ASGI server with websocket support
- `websockets` 12.0+ - WebSocket protocol
- `google-genai` 1.0.0+ - Google Gemini API client
- `pydantic` 2.0.0+ - Data validation
- `pydantic-settings` 2.0.0+ - Configuration management
- `python-dotenv` 1.0.0+ - Environment variable loading
- `pillow` 10.0.0+ - Image processing

**Critical (Frontend):**
- `next` 14.0.0 - React framework with SSR/SSG
- `react` 18.2.0 - Core React library
- `react-dom` 18.2.0 - React DOM rendering
- `lucide-react` 0.300.0 - Icon library

**Dev Dependencies (Frontend):**
- `@types/node` 20.0.0+ - Node.js types
- `@types/react` 18.2.0+ - React types
- `@types/react-dom` 18.2.0+ - React DOM types
- `autoprefixer` 10.4.16 - Vendor prefixes
- `postcss` 8.4.32 - CSS processing
- `tailwindcss` 3.4.0 - Utility CSS
- `typescript` 5.0.0+ - Type safety

## Configuration

**Environment:**
- Python: `.env` file via `pydantic-settings`
- Backend config: `backend/app/config.py` - `Config` class extending `BaseSettings`

**Key Config Settings (`backend/app/config.py`):**
```python
GEMINI_API_KEY: str
GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
CORS_ORIGINS: list[str] = ["http://localhost:3000"]
LOG_LEVEL: str = "INFO"
SESSION_TTL_SECONDS: int = 3600
```

**Build Config:**
- `frontend/tsconfig.json` - TypeScript configuration with Next.js plugin
- Path alias: `@/*` maps to `./*`
- `frontend/tailwind.config.js` - Tailwind CSS configuration

**CORS:**
- Configured via `CORS_ORIGINS` setting
- Default allowed origin: `http://localhost:3000`

## Platform Requirements

**Development:**
- Node.js 18+
- Python 3.11
- npm for frontend dependencies
- pip for backend dependencies

**Production:**
- Docker for backend containerization
- Backend: Python 3.11-slim image
- Backend exposed on port 8080
- Frontend on port 3000 (Next.js default)

---

*Stack analysis: 2026-03-07*
