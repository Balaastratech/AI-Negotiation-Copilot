# Codebase Structure

**Analysis Date:** 2026-03-10

## Directory Layout

```
project-root/
├── .agents/               # GSD agent skills and workflows
├── .opencode/            # OpenCode configuration and dependencies
├── .vscode/              # VSCode settings
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/          # API route handlers
│   │   ├── models/       # Pydantic data models
│   │   ├── services/     # Business logic
│   │   ├── config.py     # Configuration/settings
│   │   └── main.py       # FastAPI app entry point
│   ├── tests/            # Backend tests
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Container configuration
├── frontend/             # Next.js React frontend
│   ├── app/              # Next.js app router pages
│   ├── components/       # React UI components
│   │   ├── negotiation/ # Negotiation dashboard components
│   │   └── enrollment/   # Voice enrollment components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Core utilities and clients
│   ├── public/           # Static assets
│   │   └── worklets/     # Web Audio worklets
│   ├── tests/            # Frontend tests
│   ├── package.json      # Node dependencies
│   └── tsconfig.json     # TypeScript config
├── infrastructure/       # Deployment/infrastructure config
├── scripts/              # Utility scripts
├── docs/                 # Documentation
└── .planning/            # GSD planning outputs
    └── codebase/         # Codebase analysis documents
```

## Directory Purposes

### Backend (`backend/`)

**`backend/app/api/`:**
- Purpose: FastAPI route handlers
- Contains: WebSocket endpoint definition
- Key files: `backend/app/api/websocket.py`

**`backend/app/models/`:**
- Purpose: Pydantic data models
- Contains: Session, state, message type definitions
- Key files: `backend/app/models/negotiation.py`, `backend/app/models/messages.py`

**`backend/app/services/`:**
- Purpose: Business logic and external API clients
- Contains: Negotiation engine, Gemini client, connection manager
- Key files:
  - `backend/app/services/negotiation_engine.py`
  - `backend/app/services/gemini_client.py`
  - `backend/app/services/connection_manager.py`
  - `backend/app/services/master_prompt.py`

**`backend/tests/`:**
- Purpose: Python unit tests
- Contains: Test modules

### Frontend (`frontend/`)

**`frontend/app/`:**
- Purpose: Next.js app router pages
- Contains: React page components
- Key files: `frontend/app/page.tsx`, `frontend/app/negotiate/page.tsx`, `frontend/app/layout.tsx`

**`frontend/components/negotiation/`:**
- Purpose: Negotiation dashboard UI components
- Contains: Dashboard, control bar, transcript panel, strategy panel, etc.
- Key files: `NegotiationDashboard.tsx`, `ControlBar.tsx`, `TranscriptPanel.tsx`, `StrategyPanel.tsx`

**`frontend/components/enrollment/`:**
- Purpose: Voice enrollment UI
- Contains: Voice enrollment screen component

**`frontend/hooks/`:**
- Purpose: Custom React hooks for state and WebSocket management
- Key files: `useNegotiation.ts`, `useNegotiationState.ts`, `useAskAI.ts`, `useAudioWithSpeakerID.ts`

**`frontend/lib/`:**
- Purpose: Core utilities and clients
- Contains: WebSocket client, audio processing, types
- Key files: `websocket.ts`, `audio-worklet-manager.ts`, `voice-fingerprint.ts`, `types.ts`

**`frontend/public/worklets/`:**
- Purpose: Web Audio API worklet processors
- Contains: `pcm-processor.js`, `pcm-playback-processor.js`

## Key File Locations

### Entry Points

- `backend/app/main.py` - FastAPI application initialization
- `frontend/app/page.tsx` - Main frontend page

### Configuration

- `backend/app/config.py` - Backend settings (API keys, model config)
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/next.config.js` - Next.js configuration
- `frontend/tailwind.config.js` - Tailwind CSS configuration

### Core Logic

- `backend/app/services/negotiation_engine.py` - Session state machine
- `backend/app/services/gemini_client.py` - Gemini Live API integration
- `frontend/hooks/useNegotiation.ts` - WebSocket and audio management
- `frontend/lib/websocket.ts` - WebSocket client class

### Types

- `frontend/lib/types.ts` - TypeScript type definitions
- `backend/app/models/negotiation.py` - Python session models

## Naming Conventions

### Files

**Python:**
- snake_case: `negotiation_engine.py`, `gemini_client.py`

**TypeScript/React:**
- PascalCase for components: `NegotiationDashboard.tsx`, `ControlBar.tsx`
- camelCase for hooks: `useNegotiation.ts`, `useNegotiationState.ts`
- camelCase for utilities: `websocket.ts`, `audioWorkletManager.ts`

### Directories

- snake_case for Python: `backend/app/api/`, `backend/app/services/`
- kebab-case or camelCase for frontend: `components/negotiation/`, `hooks/`

### Code

- PascalCase for classes: `NegotiationSession`, `GeminiClient`, `NegotiationWebSocket`
- camelCase for functions/variables: `sendAudioChunk`, `handleStart`
- SCREAMING_SNAKE_CASE for constants: `SESSION_HARD_LIMIT_SECONDS`

## Where to Add New Code

### New Backend Feature

- API routes: `backend/app/api/`
- Business logic: `backend/app/services/`
- Models: `backend/app/models/`

### New Frontend Feature

- Page: `frontend/app/`
- Component: `frontend/components/negotiation/` or `frontend/components/enrollment/`
- Hook: `frontend/lib/` (if utility) or `frontend/hooks/` (if React state)
- Types: `frontend/lib/types.ts`

### New Service Integration

- Backend service: `backend/app/services/`
- Frontend library: `frontend/lib/`

### Tests

- Backend tests: `backend/tests/`
- Frontend tests: `frontend/tests/` or co-located with `.test.ts/.tsx`

## Special Directories

**`.planning/codebase/`:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by codebase mapper)
- Committed: Yes

**`frontend/public/worklets/`:**
- Purpose: Web Audio API worklet JavaScript files
- Generated: No
- Committed: Yes

**`backend/venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (by virtualenv/venv)
- Committed: No (should be in .gitignore)

**`frontend/node_modules/`:**
- Purpose: Node.js dependencies
- Generated: Yes (by npm install)
- Committed: No

---

*Structure analysis: 2026-03-10*
