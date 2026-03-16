# AI Negotiation Copilot

A multimodal real-time negotiation assistant powered by Google Gemini Live API. It listens to your negotiation, analyzes context in real time, and gives you live strategic coaching so you can negotiate better prices, terms, and agreements.

Built for the **Gemini Live Agent Challenge**.

---

## 🚀 Live Demo (No Setup Required)

| Service | URL |
|---|---|
| **Frontend (Live App)** | https://negotiation-frontend-219079068693.us-central1.run.app |
| **Backend Health Check** | https://negotiation-backend-219079068693.us-central1.run.app/health |

> Both services are deployed on **Google Cloud Run** in `us-central1`.
> No login required. Just open the frontend URL in **Chrome** and allow microphone access.

---

## Table of Contents

- [Live Demo](#-live-demo-no-setup-required)
- [Reproducible Testing](#-reproducible-testing)
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [How It Works](#how-it-works)
- [WebSocket API](#websocket-api)
- [Deployment](#deployment)
- [Automated Tests](#automated-tests)
- [Troubleshooting](#troubleshooting)

---

## ✅ Reproducible Testing

### Option A — Test the Live Deployed App (Fastest, No Setup)

**Requirements:** A modern browser (Chrome recommended) with a working microphone.

**Step 1 — Verify the backend is running:**
```
GET https://negotiation-backend-219079068693.us-central1.run.app/health
```
Expected response: `{"status": "healthy"}`

**Step 2 — Open the frontend:**
```
https://negotiation-frontend-219079068693.us-central1.run.app
```

**Step 3 — Run a full end-to-end test:**

1. **Allow microphone** when the browser prompts
2. Click **"I Understand, Continue"** on the privacy consent screen
3. Optionally enter a negotiation context (e.g. `"Buying a used laptop, seller asking $800"`)
4. Click **"Start Negotiation"**
5. Wait for `AI is connected` status indicator (green)
6. **Speak out loud** — say something like: *"I think $800 is too high, what do you think?"*
7. Watch the **Transcript panel** update in real time with your speech
8. Watch the **Strategy panel** update with AI coaching advice
9. Hold the **"Ask AI"** button and ask a direct question: *"What should I offer?"*
10. Listen for the **AI voice response** through your speakers
11. Click **"End Negotiation"** — see the outcome summary with effectiveness score

**Expected results at each step:**
| Step | What you should see |
|---|---|
| After Step 4 | Status changes to `AI Connecting...` then `AI Listening` |
| After Step 6 | Transcript panel shows your speech with speaker label |
| After Step 7 | Strategy panel shows negotiation advice (price analysis, recommended tactic) |
| After Step 9 | AI state changes to `AI Thinking` → `AI Speaking`, voice plays back |
| After Step 11 | Outcome summary card appears with deal score |

---

### Option B — Run Locally

**Requirements:** Python 3.11+, Node.js 18+, a Gemini API key from https://aistudio.google.com/app/apikey

**Step 1 — Clone and set up backend:**
```bash
git clone https://github.com/your-username/ai-negotiation-copilot.git
cd ai-negotiation-copilot/backend

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
CORS_ORIGINS=http://localhost:3000
```

**Step 2 — Start the backend:**
```bash
uvicorn app.main:app --reload --port 8000
```
Verify: `curl http://localhost:8000/health` → `{"status":"healthy"}`

**Step 3 — Set up and start the frontend:**
```bash
cd ../frontend
npm install
npm run dev
```

**Step 4 — Open the app:**
```
http://localhost:3000
```

Follow the same test steps as Option A above.

---

### Option C — Run Automated Tests

**Backend tests (pytest):**
```bash
cd backend
venv\Scripts\activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

**Frontend tests (Vitest):**
```bash
cd frontend
npm test                   # Run all tests once
npm run test:coverage      # With coverage report
npm run test:ui            # Interactive test UI in browser
```

---

### Option D — Redeploy to Google Cloud (Full Reproducibility)

**Requirements:** Google Cloud SDK, a GCP project with billing enabled.

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# 3. Create image registry
gcloud artifacts repositories create negotiation-app --repository-format=docker --location=us-central1

# 4. Store API key
echo -n "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=- --replication-policy=automatic

# 5. Build and deploy backend
cd backend
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/negotiation-app/backend:latest .
gcloud run deploy negotiation-backend --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/negotiation-app/backend:latest --region=us-central1 --allow-unauthenticated --port=8080 --memory=2Gi --cpu=2 --timeout=3600 --min-instances=1 --set-env-vars="GEMINI_MODEL=gemini-live-2.5-flash-native-audio,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=True" --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"

# 6. Build and deploy frontend (replace BACKEND_URL with output from step 5)
cd ../frontend
gcloud builds submit --config=cloudbuild.yaml .
gcloud run deploy negotiation-frontend --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/negotiation-app/frontend:latest --region=us-central1 --allow-unauthenticated --port=8080 --memory=1Gi --cpu=1

# 7. Update CORS
gcloud run services update negotiation-backend --region=us-central1 --update-env-vars="CORS_ORIGINS=YOUR_FRONTEND_URL"
```

---

## Overview

The AI Negotiation Copilot sits in the background during a real-world negotiation (buying a car, negotiating a salary, closing a deal) and provides live AI coaching through voice and text.

It uses a **dual-model architecture**:
- **Gemini Live** — handles real-time voice interaction with the user
- **Gemini Flash (ListenerAgent)** — runs in the background extracting prices, sentiment, and context from the conversation, then injects that intel into the Live session

---

## Features

- Real-time voice capture and transcription for both speakers
- Manual speaker identification (User / Counterparty buttons)
- Live AI coaching via Gemini Live API with audio responses
- Background market research via Google Search
- Proactive Copilot mode — AI alerts you to critical moments automatically
- Ask AI mode — hold a button to ask the AI a direct question mid-negotiation
- Response modes: Advice (detailed explanation) or Command (tactical one-liner)
- Session outcome summary with savings and effectiveness analysis
- Auto-reconnect on Gemini Live session drops

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, TailwindCSS |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| AI | Google Gemini Live API, Gemini 2.0 Flash |
| Real-time | WebSockets (binary audio + JSON control frames) |
| Audio | Web Audio API (AudioWorklet) |
| Logging | Pino (frontend), python-json-logger (backend) |
| Testing | Vitest (frontend), pytest (backend) |
| Deployment | Docker, Google Cloud Run |

---

## Project Structure

```
ai-negotiation-copilot/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Environment config (Pydantic Settings)
│   │   ├── api/
│   │   │   └── websocket.py          # WebSocket endpoint + message routing
│   │   ├── models/
│   │   │   ├── negotiation.py        # Session state machine (IDLE > CONSENTED > ACTIVE > ENDING)
│   │   │   └── messages.py           # Pydantic models for all WebSocket message types
│   │   ├── services/
│   │   │   ├── gemini_client.py      # Gemini Live API integration
│   │   │   ├── listener_agent.py     # Background context extraction (dual-model)
│   │   │   ├── negotiation_engine.py # Message routing + business logic
│   │   │   ├── market_research.py    # Google Search market intelligence
│   │   │   ├── connection_manager.py # WebSocket session tracking
│   │   │   ├── audio_buffer.py       # Circular audio buffer
│   │   │   ├── response_validator.py # AI response validation
│   │   │   └── master_prompt.py      # Gemini system prompt
│   │   └── utils/
│   │       └── logging_config.py     # Structured JSON logging
│   ├── tests/                        # pytest test suite
│   ├── requirements.txt              # Production dependencies
│   ├── requirements-dev.txt          # Dev/test dependencies
│   ├── .env.example                  # Environment variable template
│   └── Dockerfile                    # Container config (port 8080)
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Main page (dashboard entry point)
│   │   ├── layout.tsx                # Root layout
│   │   └── globals.css               # Global styles
│   ├── components/
│   │   ├── negotiation/              # NegotiationDashboard + strategy UI
│   │   ├── enrollment/               # Speaker enrollment components
│   │   └── ui/                       # Reusable UI components
│   ├── hooks/
│   │   ├── useNegotiation.ts         # Core hook: WebSocket + audio management
│   │   ├── useNegotiationState.ts    # Negotiation state reducer
│   │   └── useAskAI.ts               # Ask AI button logic
│   ├── lib/
│   │   ├── websocket.ts              # WebSocket client (text + binary frames)
│   │   ├── types.ts                  # TypeScript interfaces for all message types
│   │   └── audio-worklet-manager.ts  # Mic capture + speaker playback
│   ├── utils/
│   │   ├── api.ts                    # API helpers
│   │   └── logger.ts                 # Pino logger
│   ├── tests/                        # Vitest test suite
│   ├── package.json
│   └── next.config.js
│
├── README.md
└── .gitignore
```

---

## Prerequisites

- **Node.js** 18+ LTS — https://nodejs.org
- **Python** 3.11+ — https://python.org
- **Git** — https://git-scm.com
- **Google Gemini API Key** — https://aistudio.google.com/app/apikey

Optional (for deployment):
- **Docker** — https://docker.com
- **Google Cloud SDK** — https://cloud.google.com/sdk

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ai-negotiation-copilot.git
cd ai-negotiation-copilot
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy the environment template
cp .env.example .env
```

Open `backend/.env` and fill in your values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
GEMINI_MODEL_FALLBACK=gemini-2.0-flash-live-preview-04-09
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
SESSION_TTL_SECONDS=3600
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

The frontend auto-connects to `ws://localhost:8000/ws`. To override, create `frontend/.env.local`:

```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 4. Run the app

Open two terminals:

**Terminal 1 — Backend:**

```bash
cd backend
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`
Health check: `http://localhost:8000/health`

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:3000`

Open http://localhost:3000 in your browser and grant microphone permissions when prompted.

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Your Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.5-flash-native-audio-preview-12-2025` | Primary Gemini Live model |
| `GEMINI_MODEL_FALLBACK` | No | `gemini-2.0-flash-live-preview-04-09` | Fallback model on session drop |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins |
| `LOG_LEVEL` | No | `INFO` | DEBUG, INFO, WARNING, or ERROR |
| `SESSION_TTL_SECONDS` | No | `3600` | Session timeout in seconds |
| `GOOGLE_CLOUD_PROJECT` | yes | — | GCP project ID (Vertex AI only) |
| `GOOGLE_APPLICATION_CREDENTIALS` | yes | — | Path to GCP service account JSON (Vertex AI only) |
| `GOOGLE_GENAI_USE_VERTEXAI` | yes | false` | Use Vertex AI instead of Gemini API |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_WS_URL` | No | `ws://<host>:8000/ws` | Backend WebSocket URL |

---

## How It Works

### Session flow

```
Browser
  |
  |-- Connects to WebSocket (/ws)
  |-- Grants privacy consent
  |-- Clicks "Start Negotiation"
  |     |-- Mic capture starts (16kHz PCM, binary frames)
  |     |-- Gemini Live session opens
  |
  |-- User / Counterparty speaks
  |     |-- Audio chunks stream to backend
  |     |-- Gemini Live transcribes and analyzes
  |     |-- ListenerAgent extracts context in background
  |
  |-- AI sends back:
  |     |-- TRANSCRIPT_UPDATE  (speaker + text)
  |     |-- STATE_UPDATE       (item, prices, sentiment)
  |     |-- RESEARCH_COMPLETE  (market data)
  |     |-- AI_RESPONSE        (coaching advice)
  |
  |-- Clicks "End Negotiation"
        |-- OUTCOME_SUMMARY sent (savings, effectiveness score)
```

### Dual-model architecture

- **Gemini Live** — Real-time voice conversation. The user can speak directly to it by holding the "Ask AI" button. It responds with audio.
- **Gemini Flash (ListenerAgent)** — Runs continuously in the background, analyzing the negotiation audio. Extracts prices, sentiment, and leverage points. Injects this as `LISTENER_INTEL` into the Live session so the AI gives informed advice.

### Speaker identification

Click the "User" or "Counterparty" button before each person speaks. The backend labels the transcript accordingly. No automatic voice fingerprinting required.

---

## WebSocket API

All communication happens over a single WebSocket at `/ws`. Text frames carry JSON control messages. Binary frames carry raw PCM audio.

### Client to Server

| Message | Description |
|---|---|
| `PRIVACY_CONSENT_GRANTED` | User accepts audio monitoring |
| `START_NEGOTIATION` | Begin session with optional context string |
| `SPEAKER_IDENTIFIED` | Manual speaker label (`user` or `counterparty`) |
| `SPEAKER_STOPPED` | VAD detected silence |
| `USER_ADDRESSING_AI` | User is holding the Ask AI button |
| `START_COPILOT` | Activate proactive monitoring mode |
| `SET_RESPONSE_MODE` | Set AI response style (`advice` or `command`) |
| `END_NEGOTIATION` | End session with optional final/initial price |
| `VISION_FRAME` | Send base64 image for visual context |

Binary frames: raw 16kHz Int16 PCM audio chunks.

### Server to Client

| Message | Description |
|---|---|
| `CONNECTION_ESTABLISHED` | WebSocket ready, session ID assigned |
| `CONSENT_ACKNOWLEDGED` | Consent recorded |
| `SESSION_STARTED` | Gemini Live connected |
| `TRANSCRIPT_UPDATE` | New transcript line (speaker + text) |
| `STATE_UPDATE` | Extracted negotiation context (item, prices, sentiment) |
| `RESEARCH_STARTED` / `RESEARCH_COMPLETE` | Market research progress |
| `AI_RESPONSE` | AI coaching text |
| `STRATEGY_UPDATE` | Recommended negotiation strategy |
| `OUTCOME_SUMMARY` | Final deal analysis |
| `AI_CONNECTING` / `AI_LISTENING` / `AI_THINKING` / `AI_SPEAKING` | AI state indicators |
| `COPILOT_STARTED` | Proactive mode activated |
| `RESPONSE_MODE_SET` | Mode confirmation |
| `SESSION_RECONNECTING` | Auto-reconnect in progress |
| `AI_DEGRADED` | Feature degradation notice |
| `ERROR` | Error with code and message |

Binary frames from server: 24kHz Int16 PCM audio (Gemini voice response).

---

## Deployment

### Docker

```bash
# Build backend image
docker build -t negotiation-backend ./backend

# Run backend
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=your_key_here \
  -e CORS_ORIGINS=https://your-frontend-url.com \
  negotiation-backend
```

The backend Dockerfile uses `python:3.11-slim`, runs as a non-root user, exposes port `8080`, and includes a health check at `/health`.

For the frontend, create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### Google Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Deploy backend
gcloud run deploy negotiation-backend \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key,CORS_ORIGINS=https://your-frontend-url.com

# Deploy frontend
gcloud run deploy negotiation-frontend \
  --source ./frontend \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_WS_URL=wss://your-backend-url/ws
```

After deploying the backend, update `NEXT_PUBLIC_WS_URL` in the frontend deployment to point to the backend Cloud Run URL. Use `wss://` (not `ws://`) for HTTPS deployments.

For production, store `GEMINI_API_KEY` in Google Secret Manager and reference it in Cloud Run instead of passing it as a plain environment variable.

---

## Automated Tests

### Backend

```bash
cd backend
venv\Scripts\activate   # Windows / source venv/bin/activate on macOS/Linux

pip install -r requirements-dev.txt

pytest tests/ -v
```

### Frontend

```bash
cd frontend

npm test                  # Run once
npm run test:coverage     # With coverage report
npm run test:ui           # Interactive UI
```

---

## Troubleshooting

**Microphone not working**
- You must be on `http://localhost:3000` or an HTTPS URL — browsers block mic access on other origins.
- Check that you granted microphone permission in the browser prompt.

**WebSocket connection fails**
- Confirm the backend is running: `http://localhost:8000/health` should return `{"status": "healthy"}`.
- Check that `CORS_ORIGINS` in `backend/.env` includes `http://localhost:3000`.

**Gemini API errors**
- Verify `GEMINI_API_KEY` is set correctly in `backend/.env`.
- Confirm the model name in `GEMINI_MODEL` is available in your account/region.
- The app automatically falls back to `GEMINI_MODEL_FALLBACK` on session drops.

**Audio playback issues**
- The browser requires a user gesture before audio can play — click anywhere on the page first.
- Corrupted audio is usually a codec mismatch; the fallback model handles this automatically.

**CORS errors in browser console**
- `CORS_ORIGINS` must exactly match the frontend origin including protocol and port.
- Example: `CORS_ORIGINS=http://localhost:3000`

---

## License

Built for the Gemini Live Agent Challenge. All rights reserved by the developer.
