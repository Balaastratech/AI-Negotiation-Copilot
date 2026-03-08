# Codebase Structure

**Analysis Date:** 2026-03-07

## Directory Layout

```
ai-negotiation-copilot/
├── frontend/                    # Next.js application (minimal starter)
│   ├── app/                    # Next.js App Router pages
│   │   ├── page.tsx           # Landing page (minimal stub)
│   │   └── layout.tsx         # Root layout with metadata
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   └── tailwind.config.js
│
├── backend/                     # FastAPI application (minimal starter)
│   ├── app/                   # Main application code
│   │   ├── main.py            # FastAPI app entry point
│   │   └── config.py          # Configuration (Pydantic Settings)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── docs/                       # Documentation
├── scripts/                    # Utility scripts
├── infrastructure/            # Deployment configs
└── README.md
```

## Directory Purposes

### Frontend Directory

**`frontend/app/`**
- Purpose: Next.js App Router pages and layouts
- Contains: `layout.tsx`, `page.tsx`
- Key files: 
  - `frontend/app/page.tsx` - Landing page stub (7 lines)
  - `frontend/app/layout.tsx` - Root layout with metadata

**NOT YET CREATED (documented but not implemented):**
- `frontend/components/negotiation/` - Domain-specific components
- `frontend/components/ui/` - Reusable UI primitives
- `frontend/components/providers/` - React Context providers
- `frontend/lib/` - Core utilities (websocket, media-stream, types)
- `frontend/hooks/` - Custom React hooks
- `frontend/public/worklets/` - AudioWorklet files
- `frontend/app/negotiate/page.tsx` - Main negotiation interface
- `frontend/app/api/health/route.ts` - Frontend health check proxy

### Backend Directory

**`backend/app/`**
- Purpose: Main FastAPI application code
- Contains: `main.py`, `config.py` (minimal)
- Key files:
  - `backend/app/main.py` - FastAPI app initialization (35 lines)
  - `backend/app/config.py` - Settings configuration (14 lines)

**NOT YET CREATED (documented but not implemented):**
- `backend/app/api/` - Route handlers (health.py, websocket.py)
- `backend/app/services/` - Business logic (gemini_client, negotiation_engine, connection_manager)
- `backend/app/models/` - Pydantic data models
- `backend/app/utils/` - Helper utilities
- `backend/app/middleware/` - Middleware components
- `backend/tests/` - Backend tests

## Key File Locations

### Entry Points

- `backend/app/main.py` - FastAPI application initialization
- `frontend/app/page.tsx` - Next.js landing page
- `backend/Dockerfile` - Container definition (runs uvicorn on port 8080)

### Configuration

- `backend/app/config.py` - Settings using Pydantic
- `backend/.env.example` - Environment variable template
- `frontend/package.json` - NPM dependencies
- `frontend/tsconfig.json` - TypeScript config with path alias `@/*`

## Current Source Files

### Frontend (`frontend/app/`)

```typescript
// page.tsx - 7 lines
export default function Home() {
  return (
    <main>
      <h1>AI Negotiation Copilot</h1>
    </main>
  )
}

// layout.tsx - 18 lines
import type { Metadata } from 'next'
export const metadata: Metadata = {
  title: 'AI Negotiation Copilot',
  description: 'Multimodal real-time negotiation assistant',
}
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
```

### Backend (`backend/app/`)

```python
# main.py - 35 lines
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Negotiation Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting AI Negotiation Copilot with primary model: {settings.GEMINI_MODEL}")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/health")
async def health_check_root():
    return {"status": "healthy"}

# Placeholder for WebSocket route
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     pass
```

```python
# config.py - 14 lines
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    LOG_LEVEL: str = "INFO"
    SESSION_TTL_SECONDS: int = 360 Config:
        env0

    class_file = ".env"

settings = Config()
```

## Dependencies

### Frontend (package.json)

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.300.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0"
  }
}
```

### Backend (requirements.txt)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
websockets>=12.0
google-genai>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
pillow>=10.0.0
```

## Naming Conventions

### Files

- **TypeScript/React:** PascalCase for components (`page.tsx`), camelCase for utilities
- **Python:** snake_case for modules, PascalCase for classes
- **Configuration:** camelCase (JS) or snake_case (Python) consistent with framework

### Directories

- **Frontend:** lowercase (`app/`, `components/`, `lib/`, `hooks/`)
- **Backend:** lowercase (`app/`, `services/`, `models/`, `utils/`)

## Where to Add New Code

### New Feature (Frontend)

- Pages: `frontend/app/` (App Router)
- Components: Create `frontend/components/` directory
- Hooks: Create `frontend/hooks/` directory
- Utilities: Create `frontend/lib/` directory

### New Service (Backend)

- Routes: Create `backend/app/api/` directory
- Business logic: Create `backend/app/services/` directory
- Data models: Create `backend/app/models/` directory

### New Configuration

- Backend settings: `backend/app/config.py`
- Environment variables: `backend/.env` (never commit)

---

*Structure analysis: 2026-03-07*
