# GSD Execution Roadmap — AI Negotiation Copilot

**For use with: OpenCode + get-shit-done (GSD)**
**Deadline: March 16, 2026 (10 days)**
**Last Updated: 2026-03-06**

---

## How to Use This File with GSD

Read `OPENCODE.md` in the project root for the full setup sequence (skill installs, GSD install, path explanation).

Short version:
```
# 1. Install GSD and skills first — see OPENCODE.md Part 2
# 2. Open OpenCode in project root
opencode

# 3. Initialize GSD with this file (path required)
/gsd:new-project .planning/codebase/TASKS.md

# 4. Work through phases sequentially
/gsd:discuss-phase 1
/gsd:plan-phase 1
/gsd:execute-phase 1
/gsd:verify-work 1
# Repeat for phases 2-6
```

**Model recommendation:** Use `claude-sonnet-4-5` or better for all phases.

---

## Skill Usage Map

Skills are invoked explicitly. GSD must apply the listed skills at the moments below.
Do not write code, create files, or verify work without first activating the relevant skill.

### Always-active skills (apply throughout every phase)

| Skill | When to invoke |
|-------|---------------|
| `writing-plans` | BEFORE planning any phase — run `/gsd:plan-phase N`. Apply this skill to structure the plan. |
| `executing-plans` | BEFORE executing any phase — run `/gsd:execute-phase N`. Apply this skill to drive execution. |
| `verification-before-completion` | BEFORE marking any task done — run `/gsd:verify-work N`. Apply this skill to verify every task. |
| `systematic-debugging` | THE MOMENT anything fails — import error, test failure, silent no-output. Do not guess. Apply this skill immediately. |

### Phase-gated skills (install and invoke only when entering that phase)

| Skill | Install before | Invoke when |
|-------|---------------|-------------|
| `fastapi-templates` | Phase 2 | Writing any FastAPI route, router, lifespan, dependency injection, middleware |
| `async-python-patterns` | Phase 2 | Writing any async def, asyncio.Task, asynccontextmanager, event loop interaction |
| `python-design-patterns` | Phase 3 | Writing AudioWorklet processor files and AudioWorkletManager class |
| `api-design-principles` | Phase 4 | Designing WebSocket message contracts, TypeScript types, component props interfaces |
| `test-driven-development` | Phase 5 | Writing useNegotiation hook and any test or integration verification step |

### Skill invocation format inside tasks

Every task XML block contains a `<skills>` tag listing which installed skills to activate.
GSD must read and apply those skills before writing a single line of code for that task.
Example:
```xml
<skills>async-python-patterns, fastapi-templates</skills>
```
Means: activate both skills, let their guidance shape the implementation, then write code.

---

## Critical Reading Order for GSD Agent

Read ALL of these before executing ANY phase. No exceptions.

### Group 1 — Read first (project context and constraints)
1. `.planning/codebase/PROJECT.md` — product scope, what is in/out, hackathon constraints
2. `.planning/codebase/CONCERNS.md` — known risks and how to avoid them for each phase
3. `.planning/codebase/STACK.md` — every technology decision that is locked (Context API, Firebase, SDK versions)
4. `.planning/codebase/ARCHITECTURE.md` — system design, data flows, deployment topology

### Group 2 — Read second (implementation contracts)
5. `.planning/codebase/GEMINI_SESSION.md` — SDK import, model names, session pattern (build-breaker if wrong)
6. `.planning/codebase/AUDIO_PIPELINE.md` — AudioWorklet files, PCM format, binary frames (build-breaker if wrong)
7. `.planning/codebase/STATE_MACHINE.md` — backend state transitions, WebSocket handler, all handle_*() functions
8. `.planning/codebase/API_SCHEMAS.md` — every message payload shape, TypeScript types, mock data
9. `.planning/codebase/SYSTEM_PROMPT.md` — Gemini system prompt, strategy parser, context summary
10. `.planning/codebase/INTEGRATIONS.md` — env vars, external service configs, gcloud commands

### Group 3 — Read third (code quality and structure)
11. `.planning/codebase/CONVENTIONS.md` — Python and TypeScript style, import order, docstrings
12. `.planning/codebase/STRUCTURE.md` — every directory and file location
13. `.planning/codebase/TESTING.md` — test patterns, mock targets, pytest fixtures, async test setup

---

## Phase Overview

| Phase | Name | Days | Depends On | Outcome |
|---|---|---|---|---|
| 1 | Scaffolding | Day 1 | Nothing | Empty project structure with all configs |
| 2 | Backend Core | Days 2-3 | Phase 1 | Working WebSocket server + Gemini Live session |
| 3 | Audio Pipeline | Days 3-4 | Phase 1 | AudioWorklet capture/playback in browser |
| 4 | Frontend UI | Days 4-5 | Phase 1, 3 | Full dashboard UI with mock data |
| 5 | Intelligence | Days 6-7 | Phase 2, 3, 4 | Real Gemini negotiation intelligence end-to-end |
| 6 | Deploy & Polish | Days 8-10 | All | Running on Cloud Run, demo video, submission |

Phases 3 and 4 can run in parallel after Phase 1 completes.

---

## Phase 1: Project Scaffolding

**Goal:** Working project structure with all configs, dependencies, and empty entry point.

**Read before planning:**
- `.planning/codebase/PROJECT.md` — confirms what is in scope before creating any structure
- `.planning/codebase/STACK.md` — exact dependency versions, locked decisions
- `.planning/codebase/STRUCTURE.md` — every directory and file location
- `.planning/codebase/CONVENTIONS.md` — naming patterns before touching any file
- `.planning/codebase/CONCERNS.md` — Phase 1 risks (wrong SDK in requirements.txt is the top concern)

**Wave 1 — Directory structure and configs:**

```xml
<task id="1-01">
  <title>Create complete directory structure</title>
  <skills>writing-plans, executing-plans</skills>
  <action>
    Create all directories exactly as specified in .planning/codebase/STRUCTURE.md.
    Key directories:
    - frontend/app/
    - frontend/components/negotiation/
    - frontend/components/ui/
    - frontend/components/providers/
    - frontend/lib/
    - frontend/hooks/
    - frontend/public/worklets/   (CRITICAL: AudioWorklet .js files MUST live here, not src/ or lib/)
    - backend/app/api/
    - backend/app/services/
    - backend/app/models/
    - backend/app/utils/
    - backend/app/middleware/
    - backend/tests/
    - infrastructure/
    - docs/
    - scripts/
  </action>
  <verify>
    powershell: Test-Path frontend/public/worklets; Test-Path backend/app/services
    Expected: True True
  </verify>
</task>

<task id="1-02">
  <title>Create frontend package.json and config files</title>
  <skills>executing-plans</skills>
  <action>
    Create frontend/package.json with:
    - Next.js 14, React 18, TypeScript, TailwindCSS, lucide-react
    - Exact versions from .planning/codebase/STACK.md

    Create frontend/tsconfig.json:
    - strict mode enabled
    - path alias @/* -> ./*

    Create frontend/next.config.js
    Create frontend/tailwind.config.js
  </action>
  <verify>
    powershell: cd frontend; npm install --dry-run 2>&1 | Select-Object -First 5
    Expected: no errors
  </verify>
</task>

<task id="1-03">
  <title>Create backend requirements.txt and Dockerfile</title>
  <skills>executing-plans</skills>
  <action>
    Create backend/requirements.txt:
      fastapi>=0.109.0
      uvicorn[standard]>=0.27.0
      websockets>=12.0
      google-genai>=1.0.0        # CORRECT SDK — NOT google-generativeai
      pydantic>=2.0.0
      pydantic-settings>=2.0.0
      python-dotenv>=1.0.0
      pillow>=10.0.0

    Create backend/Dockerfile:
      FROM python:3.11-slim
      WORKDIR /app
      COPY requirements.txt .
      RUN pip install --no-cache-dir -r requirements.txt
      COPY . .
      RUN useradd -m -u 1000 appuser && chown -R appuser /app
      USER appuser
      HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8080/health || exit 1
      EXPOSE 8080
      CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

    Create backend/.env.example with all required env vars from .planning/codebase/INTEGRATIONS.md.
  </action>
  <verify>
    powershell: Select-String "google-genai" backend/requirements.txt
    Expected: match found (confirms correct SDK, not google-generativeai)
  </verify>
</task>

<task id="1-04">
  <title>Create backend entry point and config</title>
  <skills>executing-plans, verification-before-completion</skills>
  <action>
    Create backend/app/__init__.py (empty)

    Create backend/app/config.py using pydantic-settings BaseSettings:
      GEMINI_API_KEY: str
      GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-12-2025"
      GEMINI_MODEL_FALLBACK: str = "gemini-2.0-flash-live-preview-04-09"
      CORS_ORIGINS: list[str] = ["http://localhost:3000"]
      LOG_LEVEL: str = "INFO"
      SESSION_TTL_SECONDS: int = 3600

    Create backend/app/main.py:
      - FastAPI app instance with title and version
      - CORSMiddleware (allow all origins in dev, restrict via CORS_ORIGINS in prod)
      - Include routers: health router at /api, websocket router at root
      - Startup log message showing active model name
  </action>
  <verify>
    powershell: cd backend; python -c "from app.main import app; print('OK')"
    Expected: OK
  </verify>
</task>
```

---

## Phase 2: Backend Core

**Goal:** Working FastAPI WebSocket server with full Gemini Live API session management.

**Read before planning:**

### Group 1 — Read first (project context and constraints)
1. `.planning/codebase/PROJECT.md` — product scope, what is in/out, hackathon constraints
2. `.planning/codebase/CONCERNS.md` — known risks and how to avoid them for each phase
3. `.planning/codebase/STACK.md` — every technology decision that is locked (Context API, Firebase, SDK versions)
4. `.planning/codebase/ARCHITECTURE.md` — system design, data flows, deployment topology

### Group 2 — Read second (implementation contracts)
5. `.planning/codebase/GEMINI_SESSION.md` — SDK import, model names, session pattern (build-breaker if wrong)
6. `.planning/codebase/AUDIO_PIPELINE.md` — AudioWorklet files, PCM format, binary frames (build-breaker if wrong)
7. `.planning/codebase/STATE_MACHINE.md` — backend state transitions, WebSocket handler, all handle_*() functions
8. `.planning/codebase/API_SCHEMAS.md` — every message payload shape, TypeScript types, mock data
9. `.planning/codebase/SYSTEM_PROMPT.md` — Gemini system prompt, strategy parser, context summary
10. `.planning/codebase/INTEGRATIONS.md` — env vars, external service configs, gcloud commands

### Group 3 — Read third (code quality and structure)
11. `.planning/codebase/CONVENTIONS.md` — Python and TypeScript style, import order, docstrings
12. `.planning/codebase/STRUCTURE.md` — every directory and file location
13. `.planning/codebase/TESTING.md` — test patterns, mock targets, pytest fixtures, async test setup
14. `.planning/codebase/STATE_MACHINE.md`


**Wave 1 — Models and state machine:**

```xml
<task id="2-01">
  <title>Create Pydantic models</title>
  <skills>async-python-patterns, verification-before-completion</skills>
  <action>
    Create backend/app/models/__init__.py (empty)

    Create backend/app/models/negotiation.py:
      - NegotiationState enum (IDLE, CONSENTED, ACTIVE, ENDING)
      - NegotiationSession Pydantic model
      Exact implementation from .planning/codebase/STATE_MACHINE.md → Session State Model section.

    Create backend/app/models/messages.py:
      - All message payload Pydantic models
      Matching .planning/codebase/API_SCHEMAS.md exactly — every field, every type.
  </action>
  <verify>
    powershell: cd backend; python -c "from app.models.negotiation import NegotiationSession, NegotiationState; print('OK')"
    Expected: OK
  </verify>
</task>

<task id="2-02">
  <title>Create ConnectionManager</title>
  <skills>fastapi-templates, async-python-patterns</skills>
  <action>
    Create backend/app/services/__init__.py (empty)

    Create backend/app/services/connection_manager.py.
    Exact implementation from .planning/codebase/GEMINI_SESSION.md → ConnectionManager Session Storage section.
    - active_connections: dict[str, dict] storing {ws, session} per session_id
    - register(), unregister(), get_session(), send_message()
    - Module-level singleton: connection_manager = ConnectionManager()
  </action>
  <verify>
    powershell: cd backend; python -c "from app.services.connection_manager import connection_manager; print('OK')"
    Expected: OK
  </verify>
</task>
```

**Wave 2 — Gemini client and system prompt:**

```xml
<task id="2-03">
  <title>Create system_prompt.py</title>
  <skills>async-python-patterns, executing-plans</skills>
  <action>
    Create backend/app/services/system_prompt.py.
    Exact implementation from .planning/codebase/SYSTEM_PROMPT.md:
    - BASE_SYSTEM_PROMPT constant (full prompt text from that file)
    - build_system_prompt(context: str) -> str
    - Context sanitization: max 2000 chars, strip <strategy> injection attempts
  </action>
  <verify>
    powershell: cd backend; python -c "from app.services.system_prompt import build_system_prompt; p=build_system_prompt('test'); assert '{context}' not in p and 'test' in p; print('OK')"
    Expected: OK
  </verify>
</task>

<task id="2-04">
  <title>Create GeminiClient</title>
  <skills>async-python-patterns, fastapi-templates</skills>
  <action>
    Create backend/app/services/gemini_client.py.
    Full implementation from .planning/codebase/GEMINI_SESSION.md:

    - GeminiUnavailableError exception class

    - open_live_session() — MUST be @asynccontextmanager using yield.
      MUST use: async with client.aio.live.connect(model=model, config=config) as session: yield session
      MUST include in LiveConnectConfig:
        response_modalities=["AUDIO", "TEXT"]
        system_instruction=build_system_prompt(context)
        session_resumption=types.SessionResumptionConfig(handle=None)

    - send_audio_chunk(session, raw_bytes) — wraps bytes in types.Blob(mime_type="audio/pcm;rate=16000")
    - send_vision_frame(session, base64_jpeg) — wraps in types.Part for image
    - receive_responses(websocket, session_id, session) — async loop over session responses
    - handle_gemini_text(websocket, session_id, text) — parse <strategy> blocks, emit STRATEGY_UPDATE
    - monitor_session_lifetime(session_id, websocket) — 9-min handoff timer

    SDK imports (no other import is correct):
      from google import genai
      from google.genai import types
  </action>
  <verify>
    powershell: cd backend; python -c "from app.services.gemini_client import GeminiClient, GeminiUnavailableError; print('OK')"
    Expected: OK (import only — no API call required)
  </verify>
</task>
```

**Wave 3 — Negotiation engine and WebSocket endpoint:**

```xml
<task id="2-05">
  <title>Create NegotiationEngine</title>
  <skills>async-python-patterns, fastapi-templates</skills>
  <action>
    Create backend/app/services/negotiation_engine.py.
    Full implementation from .planning/codebase/STATE_MACHINE.md:

    - VALID_MESSAGES: dict[NegotiationState, list[str]]
    - ERROR_CODES: dict[NegotiationState, dict]
    - validate_message(websocket, session, message_type) -> bool
    - transition_state(session, new_state, websocket) -> None
    - handle_consent(websocket, session, payload) -> None   [IDLE → CONSENTED]
    - handle_start(websocket, session, payload) -> None
        Opens Gemini Live session via open_live_session()
        Starts asyncio.Task for receive_responses()
        Starts asyncio.Task for monitor_session_lifetime()
        [CONSENTED → ACTIVE]
    - handle_vision_frame(websocket, session, payload) -> None
    - handle_end(websocket, session, payload) -> None
        Closes Gemini session
        Computes and sends OUTCOME_SUMMARY
        [ACTIVE → ENDING → IDLE]
  </action>
  <verify>
    powershell: cd backend; python -c "from app.services.negotiation_engine import validate_message, VALID_MESSAGES; print('OK')"
    Expected: OK
  </verify>
</task>

<task id="2-06">
  <title>Create WebSocket endpoint and health API</title>
  <skills>fastapi-templates, async-python-patterns, verification-before-completion</skills>
  <action>
    Create backend/app/api/__init__.py (empty)

    Create backend/app/api/websocket.py.
    Implementation from .planning/codebase/STATE_MACHINE.md → WebSocket Handler Pattern section:
    - Accept connection, register with connection_manager, send CONNECTION_ESTABLISHED
    - receive() loop distinguishing binary frames (audio) from text frames (JSON)
    - Call validate_message() before every handler
    - Route all message types to negotiation_engine handlers
    - Handle WebSocketDisconnect and cleanup

    Create backend/app/api/health.py:
    - GET /health        — overall status
    - GET /health/ready  — readiness probe (checks Gemini API key present)
    - GET /health/live   — liveness probe (always 200 if process running)

    Register both routers in backend/app/main.py.
  </action>
  <verify>
    powershell: cd backend; Start-Process uvicorn -ArgumentList "app.main:app --host 0.0.0.0 --port 8080" -NoNewWindow; Start-Sleep 3; Invoke-WebRequest http://localhost:8080/health | ConvertFrom-Json; Stop-Process -Name uvicorn -ErrorAction SilentlyContinue
    Expected: status = "healthy"
  </verify>
</task>
```

---

## Phase 3: Audio Pipeline

**Goal:** Browser captures PCM audio via AudioWorklet and streams binary frames to backend. Backend plays Gemini audio responses back via AudioWorklet.

**Install skill before planning:**
```powershell
npx skills add https://github.com/wshobson/agents --skill python-design-patterns -a opencode
```

**Read before planning:**

**Read before planning:**

### Group 1 — Read first (project context and constraints)
1. `.planning/codebase/PROJECT.md` — product scope, what is in/out, hackathon constraints
2. `.planning/codebase/CONCERNS.md` — known risks and how to avoid them for each phase
3. `.planning/codebase/STACK.md` — every technology decision that is locked (Context API, Firebase, SDK versions)
4. `.planning/codebase/ARCHITECTURE.md` — system design, data flows, deployment topology

### Group 2 — Read second (implementation contracts)
5. `.planning/codebase/GEMINI_SESSION.md` — SDK import, model names, session pattern (build-breaker if wrong)
6. `.planning/codebase/AUDIO_PIPELINE.md` — AudioWorklet files, PCM format, binary frames (build-breaker if wrong)
7. `.planning/codebase/STATE_MACHINE.md` — backend state transitions, WebSocket handler, all handle_*() functions
8. `.planning/codebase/API_SCHEMAS.md` — every message payload shape, TypeScript types, mock data
9. `.planning/codebase/SYSTEM_PROMPT.md` — Gemini system prompt, strategy parser, context summary
10. `.planning/codebase/INTEGRATIONS.md` — env vars, external service configs, gcloud commands

### Group 3 — Read third (code quality and structure)
11. `.planning/codebase/CONVENTIONS.md` — Python and TypeScript style, import order, docstrings
12. `.planning/codebase/STRUCTURE.md` — every directory and file location
13. `.planning/codebase/TESTING.md` — test patterns, mock targets, pytest fixtures, async test setup

**Wave 1 — Worklet files:**

```xml
<task id="3-01">
  <title>Create pcm-processor.js — capture worklet</title>
  <skills>python-design-patterns, executing-plans</skills>
  <action>
    Create frontend/public/worklets/pcm-processor.js.
    Exact implementation from .planning/codebase/AUDIO_PIPELINE.md → File 1.

    Class: PCMCaptureProcessor extends AudioWorkletProcessor
    - _bufferSize: 4096 samples (~256ms at 16kHz)
    - process(): converts Float32 input → Int16, buffers until 4096 samples
    - Posts Int16Array.buffer via this.port.postMessage(int16.buffer, [int16.buffer])
    - Returns true to keep processor alive

    registerProcessor('pcm-capture-processor', PCMCaptureProcessor)

    FILE MUST be in frontend/public/worklets/ — NOT in src/ or lib/.
    Reason: audioWorklet.addModule('/worklets/pcm-processor.js') requires a served URL.
  </action>
  <verify>
    powershell: Test-Path frontend/public/worklets/pcm-processor.js; Select-String "registerProcessor" frontend/public/worklets/pcm-processor.js
    Expected: True + match found
  </verify>
</task>

<task id="3-02">
  <title>Create pcm-playback-processor.js — playback worklet</title>
  <skills>python-design-patterns, executing-plans</skills>
  <action>
    Create frontend/public/worklets/pcm-playback-processor.js.
    Exact implementation from .planning/codebase/AUDIO_PIPELINE.md → File 2.

    Class: PCMPlaybackProcessor extends AudioWorkletProcessor
    - _queue: Int16Array[] with overflow protection (max 3 seconds = 24000*2*3 bytes)
    - port.onmessage: receives Int16Array chunks from main thread, drops oldest on overflow
    - process(): converts Int16 → Float32 output, fills silence when queue empty
    - Returns true to keep processor alive

    registerProcessor('pcm-playback-processor', PCMPlaybackProcessor)
  </action>
  <verify>
    powershell: Test-Path frontend/public/worklets/pcm-playback-processor.js; Select-String "registerProcessor" frontend/public/worklets/pcm-playback-processor.js
    Expected: True + match found
  </verify>
</task>

<task id="3-03">
  <title>Create AudioWorkletManager TypeScript class</title>
  <skills>python-design-patterns, api-design-principles</skills>
  <action>
    Create frontend/lib/audio-worklet-manager.ts.
    Exact implementation from .planning/codebase/AUDIO_PIPELINE.md → File 3.

    Class: AudioWorkletManager
    - captureContext: AudioContext at sampleRate: 16000  (forces 16kHz capture)
    - playbackContext: AudioContext at sampleRate: 24000 (matches Gemini output)
    - startCapture(onChunk: (buffer: ArrayBuffer) => void): Promise<void>
    - initPlayback(): Promise<void>
    - playChunk(chunk: ArrayBuffer): void — zero-copy transfer via postMessage
    - stopCapture(): void
    - cleanup(): void — call on session end or component unmount
    - get isCapturing(): boolean
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit lib/audio-worklet-manager.ts 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>
```

**Wave 2 — WebSocket client with binary frame support:**

```xml
<task id="3-04">
  <title>Create WebSocket client with binary frame handling</title>
  <skills>api-design-principles, async-python-patterns</skills>
  <action>
    Create frontend/lib/websocket.ts.
    Implementation from .planning/codebase/API_SCHEMAS.md → Frontend WebSocket Frame Types section.

    Must handle TWO distinct frame types in ws.onmessage:
    - event.data instanceof ArrayBuffer or Blob → binary PCM audio → route to playChunk()
    - event.data is string → JSON control message → parse and dispatch

    Methods:
    - sendAudioChunk(pcmBuffer: ArrayBuffer): void
        ws.send(pcmBuffer)  ← BINARY frame, NOT JSON
    - sendControl(type: string, payload: unknown): void
        ws.send(JSON.stringify({ type, payload }))  ← TEXT frame
    - connect(url: string, handlers: MessageHandlers): void
        auto-reconnect with exponential backoff (max 5 attempts: 1s,2s,4s,8s,16s)
    - disconnect(): void

    On SESSION_RECONNECTING: do NOT disconnect, show non-blocking status only.
    On AUDIO_INTERRUPTED: call audioManager method to clear playback queue.
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit lib/websocket.ts 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>
```

---

## Phase 4: Frontend UI

**Goal:** Complete negotiation dashboard UI wired to mock data. No live backend needed for this phase.

**Install skill before planning:**
```powershell
npx skills add https://github.com/wshobson/agents --skill api-design-principles
```

**Read before planning:**

### Group 1 — Read first (project context and constraints)
1. `.planning/codebase/PROJECT.md` — product scope, what is in/out, hackathon constraints
2. `.planning/codebase/CONCERNS.md` — known risks and how to avoid them for each phase
3. `.planning/codebase/STACK.md` — every technology decision that is locked (Context API, Firebase, SDK versions)
4. `.planning/codebase/ARCHITECTURE.md` — system design, data flows, deployment topology

### Group 2 — Read second (implementation contracts)
5. `.planning/codebase/GEMINI_SESSION.md` — SDK import, model names, session pattern (build-breaker if wrong)
6. `.planning/codebase/AUDIO_PIPELINE.md` — AudioWorklet files, PCM format, binary frames (build-breaker if wrong)
7. `.planning/codebase/STATE_MACHINE.md` — backend state transitions, WebSocket handler, all handle_*() functions
8. `.planning/codebase/API_SCHEMAS.md` — every message payload shape, TypeScript types, mock data
9. `.planning/codebase/SYSTEM_PROMPT.md` — Gemini system prompt, strategy parser, context summary
10. `.planning/codebase/INTEGRATIONS.md` — env vars, external service configs, gcloud commands

### Group 3 — Read third (code quality and structure)
11. `.planning/codebase/CONVENTIONS.md` — Python and TypeScript style, import order, docstrings
12. `.planning/codebase/STRUCTURE.md` — every directory and file location
13. `.planning/codebase/TESTING.md` — test patterns, mock targets, pytest fixtures, async test setup

**Wave 1 — Types and mock data:**

```xml
<task id="4-01">
  <title>Create types.ts and mock-data.ts</title>
  <skills>api-design-principles, executing-plans</skills>
  <action>
    Create frontend/lib/types.ts.
    Copy VERBATIM from .planning/codebase/API_SCHEMAS.md → TypeScript Type Definitions section.
    Do not rename fields, do not invent new types, do not omit any type.
    Includes: ClientMessageType, ServerMessageType, WebSocketMessage,
              TranscriptEntry, Strategy, OutcomeSummary, NegotiationState,
              INITIAL_NEGOTIATION_STATE

    Create frontend/lib/mock-data.ts.
    Copy from .planning/codebase/API_SCHEMAS.md → Mock Data section.
    Includes: MOCK_STRATEGY, MOCK_TRANSCRIPT
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit lib/types.ts 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>
```

**Wave 2 — Negotiation components:**

```xml
<task id="4-02">
  <title>Create PrivacyConsent component</title>
  <skills>api-design-principles, executing-plans</skills>
  <action>
    Create frontend/components/negotiation/PrivacyConsent.tsx.
    Props: onConsent(version: string, mode: 'live' | 'roleplay') => void

    UI:
    - Full-screen modal overlay, blocks all interaction until consent given
    - Legal text explaining audio/video capture
    - Mode selection toggle: "Live Negotiation" vs "Roleplay Demo"
    - Checkbox: "I understand and agree"
    - "Start" button (disabled until checkbox checked)

    TailwindCSS only. No inline styles.
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit components/negotiation/PrivacyConsent.tsx 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>

<task id="4-03">
  <title>Create VideoCapture component</title>
  <skills>api-design-principles, executing-plans</skills>
  <action>
    Create frontend/components/negotiation/VideoCapture.tsx.
    Props: onFrameCapture(base64: string) => void; isActive: boolean

    UI states:
    - No permission: "Enable Camera" button
    - Permission granted: live video feed via <video> element
    - Error: permission denied message, no camera message

    Behavior:
    - Capture 1 frame/sec via canvas when isActive=true
    - Compress to JPEG at 0.8 quality, return base64 string (no data: prefix)
    - Uses MediaStreamManager from lib/media-stream.ts — camera ONLY, no audio methods
    - Stop all tracks on unmount
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit components/negotiation/VideoCapture.tsx 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>

<task id="4-04">
  <title>Create StrategyPanel component</title>
  <skills>api-design-principles, executing-plans</skills>
  <action>
    Create frontend/components/negotiation/StrategyPanel.tsx.
    Props: strategy: Strategy | null; isLoading: boolean

    Displays (when strategy present):
    - recommended_response: large, prominent text — this is the most important element
    - target_price and current_offer: side by side
    - key_points: bulleted list
    - approach_type: colored badge (aggressive=red, collaborative=green, walkaway=orange)
    - confidence: progress bar 0-100%
    - walkaway_threshold: shown if present
    - web_search_used + search_sources: small indicator at bottom

    States:
    - isLoading=true: skeleton pulse animation on all fields
    - strategy=null, isLoading=false: "Waiting for negotiation to start..."
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit components/negotiation/StrategyPanel.tsx 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>

<task id="4-05">
  <title>Create TranscriptPanel component</title>
  <skills>api-design-principles, executing-plans</skills>
  <action>
    Create frontend/components/negotiation/TranscriptPanel.tsx.
    Props: transcript: TranscriptEntry[]

    Features:
    - Auto-scroll to latest entry on every new message
    - Speaker color coding:
        user         → blue
        counterparty → gray
        ai           → green
    - Timestamp shown for each entry (human-readable, e.g. "2:34 PM")
    - Empty state: "Conversation will appear here..."
    - Scrollable container with fixed height
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit components/negotiation/TranscriptPanel.tsx 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>

<task id="4-06">
  <title>Create ControlBar and NegotiationDashboard</title>
  <skills>api-design-principles, executing-plans, verification-before-completion</skills>
  <action>
    Create frontend/components/negotiation/ControlBar.tsx.
    Props: onStart, onEnd, onToggleCamera, onToggleAudio, isActive: boolean, isAudioActive: boolean, isCameraActive: boolean
    Buttons:
    - Start (green, disabled if isActive)
    - End (red, disabled if not isActive)
    - Camera toggle (shows active/inactive state visually)
    - Mic toggle (shows active/inactive state visually)
    - Privacy indicator dot (red pulsing when recording)

    Create frontend/components/negotiation/NegotiationDashboard.tsx.
    Uses: all negotiation components + useNegotiation hook (import even if hook is stub at this phase)
    Layout: 2-column
    - Left column: VideoCapture + ControlBar
    - Right column: StrategyPanel (top) + TranscriptPanel (bottom, scrollable)

    Create UI primitives:
    - frontend/components/ui/Button.tsx
    - frontend/components/ui/Card.tsx
    - frontend/components/ui/Toggle.tsx
    - frontend/components/ui/Badge.tsx

    Create pages:
    - frontend/app/layout.tsx — root layout with NegotiationProvider wrapper
    - frontend/app/globals.css — TailwindCSS base imports
    - frontend/app/page.tsx — landing page with "Start Negotiation" CTA button linking to /negotiate
    - frontend/app/negotiate/page.tsx — renders NegotiationDashboard inside PrivacyConsent gate
    - frontend/app/api/health/route.ts — returns { status: "ok" }
  </action>
  <verify>
    powershell: cd frontend; npm run build 2>&1 | Select-Object -Last 20
    Expected: Build successful, no TypeScript errors
  </verify>
</task>

<task id="4-07">
  <title>Create NegotiationProvider and MediaStreamManager</title>
  <skills>api-design-principles, async-python-patterns, verification-before-completion</skills>
  <action>
    Create frontend/components/providers/NegotiationProvider.tsx.
    - NegotiationContext using React Context API (locked decision — no Zustand)
    - useReducer with NegotiationState from types.ts as state shape
    - Initial state: INITIAL_NEGOTIATION_STATE from types.ts
    - Reducer handles actions: SET_STRATEGY, APPEND_TRANSCRIPT, SET_OUTCOME,
      SET_CONNECTED, SET_NEGOTIATING, SET_CONSENTED, SET_DEGRADED, SET_ERROR, RESET
    - Export: NegotiationProvider component, useNegotiationContext hook

    Create frontend/lib/media-stream.ts.
    Class: MediaStreamManager
    - requestCameraAccess(): Promise<MediaStream>  — video only, no audio
    - captureFrame(videoElement: HTMLVideoElement): string  — returns base64 JPEG
    - startFrameCapture(videoElement, onFrame, fps=1): void  — setInterval at 1fps
    - stopFrameCapture(): void
    - cleanup(): void  — stops all tracks

    NO audio methods on this class. Audio is exclusively AudioWorkletManager's responsibility.
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit components/providers/NegotiationProvider.tsx lib/media-stream.ts 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>
```

---

## Phase 5: Intelligence Integration

**Goal:** Connect live frontend to live backend with real Gemini negotiation intelligence end-to-end.

**Install skill before planning:**
```powershell
npx skills add obra/superpowers --skill test-driven-development -a opencode
```

**Prerequisites:** Phases 2, 3, 4 complete. Backend health check passing locally.

**Read before planning:**

### Group 1 — Read first (project context and constraints)
1. `.planning/codebase/PROJECT.md` — product scope, what is in/out, hackathon constraints
2. `.planning/codebase/CONCERNS.md` — known risks and how to avoid them for each phase
3. `.planning/codebase/STACK.md` — every technology decision that is locked (Context API, Firebase, SDK versions)
4. `.planning/codebase/ARCHITECTURE.md` — system design, data flows, deployment topology

### Group 2 — Read second (implementation contracts)
5. `.planning/codebase/GEMINI_SESSION.md` — SDK import, model names, session pattern (build-breaker if wrong)
6. `.planning/codebase/AUDIO_PIPELINE.md` — AudioWorklet files, PCM format, binary frames (build-breaker if wrong)
7. `.planning/codebase/STATE_MACHINE.md` — backend state transitions, WebSocket handler, all handle_*() functions
8. `.planning/codebase/API_SCHEMAS.md` — every message payload shape, TypeScript types, mock data
9. `.planning/codebase/SYSTEM_PROMPT.md` — Gemini system prompt, strategy parser, context summary
10. `.planning/codebase/INTEGRATIONS.md` — env vars, external service configs, gcloud commands

### Group 3 — Read third (code quality and structure)
11. `.planning/codebase/CONVENTIONS.md` — Python and TypeScript style, import order, docstrings
12. `.planning/codebase/STRUCTURE.md` — every directory and file location
13. `.planning/codebase/TESTING.md` — test patterns, mock targets, pytest fixtures, async test setup

**Wave 1 — Backend intelligence additions:**

```xml
<task id="5-01">
  <title>Add strategy parser and context summary to negotiation_engine.py</title>
  <skills>async-python-patterns, executing-plans</skills>
  <action>
    Extend backend/app/services/negotiation_engine.py — do NOT replace existing code.

    Add handle_gemini_text(websocket, session_id, text):
      - STRATEGY_PATTERN = re.compile(r'<strategy>(.*?)</strategy>', re.DOTALL)
      - Extract all <strategy>...</strategy> blocks, parse as JSON, send STRATEGY_UPDATE
      - Strip strategy blocks from text, send remaining as AI_RESPONSE (coaching type)
      - Non-fatal on JSONDecodeError: log warning, keep last known strategy
      Source: .planning/codebase/SYSTEM_PROMPT.md → Parsing Strategy JSON section

    Add _build_context_summary(session: NegotiationSession) -> str:
      - Builds continuation context for Gemini session handoff at 9 minutes
      - Includes: original context, last strategy, last 10 transcript entries
      Source: .planning/codebase/SYSTEM_PROMPT.md → Continuation Context section
  </action>
  <verify>
    powershell: cd backend; python -c "from app.services.negotiation_engine import handle_gemini_text; print('OK')"
    Expected: OK
  </verify>
</task>
```

**Wave 2 — Frontend hook:**

```xml
<task id="5-02">
  <title>Create useNegotiation hook</title>
  <skills>test-driven-development, api-design-principles, async-python-patterns</skills>
  <action>
    Create frontend/hooks/useNegotiation.ts.
    Connects: WebSocketClient + AudioWorkletManager + MediaStreamManager + NegotiationContext.

    Handles ALL ServerMessageType messages:
      binary frame (ArrayBuffer/Blob) → audioManager.playChunk(buffer)
      CONNECTION_ESTABLISHED         → dispatch SET_CONNECTED
      CONSENT_ACKNOWLEDGED           → dispatch SET_CONSENTED
      SESSION_STARTED                → dispatch SET_NEGOTIATING, store model info
      TRANSCRIPT_UPDATE              → dispatch APPEND_TRANSCRIPT
      STRATEGY_UPDATE                → dispatch SET_STRATEGY
      AI_RESPONSE                    → dispatch APPEND_TRANSCRIPT (speaker: 'ai')
      OUTCOME_SUMMARY                → dispatch SET_OUTCOME, dispatch SET_NEGOTIATING false
      AUDIO_INTERRUPTED              → clear audioManager playback queue
      SESSION_RECONNECTING           → dispatch SET_ERROR with non-blocking status message
      AI_DEGRADED                    → dispatch SET_DEGRADED
      ERROR                          → dispatch SET_ERROR

    Exposes:
      connect(wsUrl: string): void
      grantConsent(version: string, mode: string): void
      startNegotiation(context: string): void
      endNegotiation(finalPrice?: number, initialPrice?: number): void
      sendFrame(base64: string): void
      state: NegotiationState  (from context)
  </action>
  <verify>
    powershell: cd frontend; npx tsc --noEmit hooks/useNegotiation.ts 2>&1 | Select-Object -First 5
    Expected: no TypeScript errors
  </verify>
</task>
```

**Wave 3 — End-to-end integration test:**

```xml
<task id="5-03">
  <title>End-to-end integration test</title>
  <skills>test-driven-development, systematic-debugging, verification-before-completion</skills>
  <action>
    Start backend:
      cd backend
      .\venv\Scripts\activate
      uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

    Start frontend (new terminal):
      cd frontend
      npm run dev

    Manual test sequence — all 8 steps must pass:
      1. Open http://localhost:3000/negotiate
      2. Accept privacy consent (choose "live" mode)
      3. Enable camera — verify video feed appears
      4. Click Start Negotiation — context: "buying a used laptop, seller asking $500"
      5. Speak: "I'm interested in this laptop, what's your best price?"
      6. Verify: transcript panel updates with user speech
      7. Verify: strategy panel updates with AI recommendation and target price
      8. Verify: audio response plays through speaker
      9. Click End Negotiation
      10. Verify: OUTCOME_SUMMARY modal appears with deal analysis

    Fix any integration issues before marking complete.
  </action>
  <verify>
    powershell: Invoke-WebRequest http://localhost:8080/health | ConvertFrom-Json
    Expected: status = "healthy"
    Manual: all 10 steps above complete without error
  </verify>
</task>
```

---

## Phase 6: Deployment and Submission

**Goal:** Live on Cloud Run and Firebase Hosting with demo video and all submission materials.

**Read before planning:**
- `.planning/codebase/STACK.md` — Firebase Hosting only, no Vercel
- `.planning/codebase/ARCHITECTURE.md` — Cloud Run deployment flags, --min-instances=1 requirement
- `.planning/codebase/INTEGRATIONS.md` — env vars, Secret Manager setup, gcloud commands
- `.planning/codebase/PROJECT.md` — hackathon submission requirements and README wording
- `.planning/codebase/CONCERNS.md` — deployment risks (cold start, WebSocket timeout documented here)

**Wave 1 — Cloud Run deployment:**

```xml
<task id="6-01">
  <title>Deploy backend to Cloud Run</title>
  <skills>executing-plans, verification-before-completion</skills>
  <action>
    Create backend/cloudbuild.yaml:
      steps:
        - name: 'gcr.io/cloud-builders/docker'
          args: ['build', '-t', 'gcr.io/$PROJECT_ID/ai-negotiation-copilot-backend', '.']
      images: ['gcr.io/$PROJECT_ID/ai-negotiation-copilot-backend']

    Create infrastructure/deploy.sh:
      gcloud builds submit ./backend --config=backend/cloudbuild.yaml

      gcloud run deploy ai-negotiation-copilot-backend \
        --image=gcr.io/$PROJECT_ID/ai-negotiation-copilot-backend \
        --platform=managed \
        --region=us-central1 \
        --allow-unauthenticated \
        --min-instances=1 \
        --max-instances=3 \
        --memory=1Gi \
        --cpu=2 \
        --timeout=3600 \
        --set-env-vars="GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025"

    CRITICAL: --min-instances=1 prevents cold starts killing the demo.
    CRITICAL: --timeout=3600 allows WebSocket sessions to stay open.

    Set GEMINI_API_KEY via Secret Manager or --set-env-vars (never commit to repo).

    Run deploy.sh and verify health endpoint responds.
  </action>
  <verify>
    powershell: Invoke-WebRequest https://YOUR-SERVICE.run.app/health | ConvertFrom-Json
    Expected: status = "healthy"
  </verify>
</task>

<task id="6-02">
  <title>Deploy frontend to Firebase Hosting</title>
  <skills>executing-plans, verification-before-completion</skills>
  <action>
    Set Cloud Run WebSocket URL in frontend/.env.production:
      NEXT_PUBLIC_WS_URL=wss://YOUR-SERVICE.run.app/ws
      NEXT_PUBLIC_API_URL=https://YOUR-SERVICE.run.app

    Initialize Firebase Hosting:
      npm install -g firebase-tools
      firebase login
      firebase init hosting
        → select existing GCP project
        → set public directory to "out" (static export) or ".next" (if using Next.js adapter)
        → configure as single-page app: yes

    Build and deploy:
      cd frontend
      npm run build
      firebase deploy --only hosting

    DECISION: Firebase Hosting ONLY. Do NOT use Vercel or Netlify.
    Reason: Keeps all deployment in GCP console — Firebase counts as Google Cloud proof.

    Verify deployed frontend connects to Cloud Run backend by completing a full negotiation.
  </action>
  <verify>
    Manual: Open deployed Firebase URL, complete full negotiation session end-to-end.
    Expected: works identically to local dev.
  </verify>
</task>

<task id="6-03">
  <title>README, architecture diagram, and demo video</title>
  <skills>writing-plans, executing-plans, verification-before-completion</skills>
  <action>
    Create/update README.md with:
    - Project description (2 paragraphs — see .planning/codebase/PROJECT.md for wording)
    - Tech stack table (frontend, backend, AI, deployment)
    - Local setup instructions step by step (venv, npm install, env vars, run commands)
    - Environment variables table (all vars from .env.example with descriptions)
    - Cloud Run deployment instructions (point to infrastructure/deploy.sh)
    - Live demo link (Firebase Hosting URL)
    - Demo video link (add after recording)

    Create docs/architecture-diagram.md with Mermaid diagram:
      Browser
        → AudioWorklet (16kHz PCM capture)
        → Next.js Frontend (Firebase Hosting)
        → [WebSocket binary frames / JSON text frames]
        → FastAPI Backend (Cloud Run)
        → Gemini Live API
        → [audio 24kHz / strategy JSON / transcript]
        → FastAPI Backend
        → Next.js Frontend
        → AudioWorklet (24kHz PCM playback)
      Include Google Search tool branch from Gemini.
      (Judges require an architecture diagram — do not skip)

    Record demo video (max 4 minutes):
    - Show live audio capture and Gemini audio response
    - Show camera feed + vision analysis in strategy panel
    - Show strategy panel updating in real time
    - Show Cloud Run console URL in browser tab (proof of GCP deployment)
    - Show outcome summary at session end
    Upload to YouTube or Vimeo (unlisted is fine), add link to README.md.
  </action>
  <verify>
    powershell: Test-Path README.md; Test-Path docs/architecture-diagram.md
    Expected: True True
  </verify>
</task>
```

---

## Hackathon Submission Checklist

**Required (disqualified without these):**
- [ ] Backend live on Cloud Run — health endpoint responds at public URL
- [ ] Frontend live on Firebase Hosting — public URL accessible
- [ ] Public GitHub repository with all source code
- [ ] `README.md` with setup and deployment instructions
- [ ] Architecture diagram (`docs/architecture-diagram.md`)
- [ ] Demo video — max 4 minutes, English, YouTube or Vimeo
  - Live audio + vision in real-time (no mockups)
  - Strategy panel updating during negotiation
  - Cloud Run console visible as proof of GCP deployment
  - Outcome summary at session end

**Optional (bonus points — skip if behind):**
- [ ] Google Search grounding wired into `LiveConnectConfig`
- [ ] Session resumption via Gemini resumption handles
- [ ] Multi-context presets (salary, car, vendor)
- [ ] Blog post (#GeminiLiveAgentChallenge)
- [ ] `infrastructure/deploy.sh` counts as deployment automation bonus

---

## What to Skip (10-Day Triage)

These will NOT be implemented for the hackathon:

- ❌ Redis session storage — in-memory is fine for demo scale
- ❌ JWT authentication — public demo URL needs no auth
- ❌ E2E automated tests — manual testing only
- ❌ Terraform IaC — deploy.sh is sufficient
- ❌ Rate limiting middleware — not needed at demo scale

---

*GSD roadmap: 2026-03-06*
