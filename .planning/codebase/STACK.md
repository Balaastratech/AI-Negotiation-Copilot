# Technology Stack

**Analysis Date:** 2026-03-10

## Languages

**Primary:**
- TypeScript 5.x - Frontend UI and client-side logic
- Python 3.11 - Backend API and AI integration

**Secondary:**
- CSS - Styling via Tailwind CSS

## Runtime

**Environment:**
- Node.js 20.x - Frontend development server (Next.js)
- Python 3.11 - Backend runtime

**Package Managers:**
- npm (frontend) - `package-lock.json` present
- pip (backend) - `requirements.txt`

## Frameworks

**Frontend:**
- Next.js 15.x - React framework with App Router
- React 19.x - UI library

**Backend:**
- FastAPI 0.109+ - REST API and WebSocket server
- Uvicorn - ASGI server

**Testing:**
- Vitest 4.x - Frontend testing framework
- pytest - Backend testing

**Styling:**
- Tailwind CSS 3.4 - Utility-first CSS framework
- PostCSS - CSS processing

## Key Dependencies

**Frontend:**
- `next` 15.x - Next.js framework
- `react` 19.x - React library
- `lucide-react` 0.470.x - Icon library

**Backend:**
- `fastapi` 0.109+ - Web framework
- `uvicorn[standard]` 0.27+ - ASGI server
- `google-genai` 1.0+ - Gemini Live API client
- `websockets` 12.0+ - WebSocket support
- `pydantic` 2.0+ - Data validation
- `pydantic-settings` 2.0+ - Settings management
- `python-dotenv` 1.0+ - Environment variable loading

**Development:**
- `typescript` 5.x - Type safety
- `vitest` 4.x - Testing
- `tailwindcss` 3.4 - Styling
- `autoprefixer` - CSS vendor prefixes

## Configuration

**Environment:**
- `.env` files (backend) - Configuration via `python-dotenv`
- Pydantic `BaseSettings` - Type-safe configuration management
- Config file: `backend/app/config.py`

**Build:**
- `frontend/next.config.js` - Next.js configuration
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/tailwind.config.js` - Tailwind CSS configuration
- `frontend/postcss.config.js` - PostCSS configuration

## Platform Requirements

**Development:**
- Node.js 20.x+
- Python 3.11+
- npm for frontend dependencies

**Production:**
- Docker container (Python 3.11-slim based)
- Exposed port: 8080 (backend)
- CORS configured for localhost:3000 (dev)

---

*Stack analysis: 2026-03-10*
