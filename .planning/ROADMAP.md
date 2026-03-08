# GSD Roadmap — AI Negotiation Copilot

**Project:** AI Negotiation Copilot  
**Created:** 2026-03-06  
**Deadline:** March 16, 2026 (10 days)

---

## Phases

| Phase | Name | Days | Depends On | Outcome |
|-------|------|------|------------|---------|
| 1 | Project Scaffolding | Day 1 | Nothing | Empty project structure with all configs |
| 2 | Backend Core | Days 2-3 | Phase 1 | Working WebSocket server + Gemini Live session |
| 3 | Audio Pipeline | Days 3-4 | Phase 1 | AudioWorklet capture/playback in browser |
| 4 | Frontend UI | Days 4-5 | Phase 1, 3 | Full dashboard UI with mock data |
| 5 | Intelligence | Days 6-7 | Phase 2, 3, 4 | Real Gemini negotiation intelligence end-to-end |
| 6 | Deploy & Polish | Days 8-10 | All | Running on Cloud Run, demo video, submission |

---

## Phase Details

### Phase 1: Project Scaffolding
- **Goal:** Working project structure with all configs, dependencies, and empty entry point
- **Tasks:** Create directory structure, frontend configs, backend requirements.txt and Dockerfile, entry points
- **Read:** PROJECT.md, STACK.md, STRUCTURE.md, CONVENTIONS.md, CONCERNS.md

**Plans:**
- [ ] 01-project-scaffolding/01-01-PLAN.md — Project scaffolding (4 tasks)

### Phase 2: Backend Core
- **Goal:** Working FastAPI WebSocket server with full Gemini Live API session management
- **Tasks:** Pydantic models, ConnectionManager, GeminiClient, NegotiationEngine, WebSocket endpoint
- **Read:** GEMINI_SESSION.md, STATE_MACHINE.md, API_SCHEMAS.md, ARCHITECTURE.md, INTEGRATIONS.md

**Plans:**
- [x] 02-backend-core/02-01-PLAN.md — Core Models & Connection Management (3 tasks) ✅
- [ ] 02-backend-core/02-02-PLAN.md — Gemini Live API Integration (3 tasks)
- [ ] 02-backend-core/02-03-PLAN.md — Negotiation Engine & WebSocket Endpoint (3 tasks)

### Phase 3: Audio Pipeline
- **Goal:** Browser captures PCM audio via AudioWorklet and streams to backend. Backend plays Gemini audio responses back.
- **Tasks:** pcm-processor.js, pcm-playback-processor.js, AudioWorkletManager, WebSocket client with binary frames
- **Read:** AUDIO_PIPELINE.md, API_SCHEMAS.md, CONCERNS.md

### Phase 4: Frontend UI
- **Goal:** Complete negotiation dashboard UI wired to mock data
- **Tasks:** Types, mock data, PrivacyConsent, VideoCapture, StrategyPanel, TranscriptPanel, ControlBar, NegotiationDashboard
- **Read:** API_SCHEMAS.md, STACK.md, STRUCTURE.md, CONVENTIONS.md

### Phase 5: Intelligence Integration
- **Goal:** Connect live frontend to live backend with real Gemini negotiation intelligence end-to-end
- **Tasks:** Strategy parser, context summary, useNegotiation hook, E2E integration test
- **Read:** SYSTEM_PROMPT.md, GEMINI_SESSION.md, STATE_MACHINE.md, API_SCHEMAS.md

### Phase 6: Deployment and Submission
- **Goal:** Live on Cloud Run and Firebase Hosting with demo video
- **Tasks:** Deploy backend to Cloud Run, deploy frontend to Firebase, create README and architecture diagram
- **Read:** STACK.md, ARCHITECTURE.md, INTEGRATIONS.md, PROJECT.md

---

*Roadmap created: 2026-03-06*
