# AI Negotiation Copilot - Developer Handoff Package

## 🎯 Project Overview

The **AI Negotiation Copilot** is a multimodal real-time negotiation assistant built for the Gemini Live Agent Challenge. It helps users obtain better prices, terms, and agreements during real-world negotiations by providing live strategic support through vision, voice, and text interaction.

### Key Features
- 📹 **Vision Analysis**: Captures and analyzes negotiation context from camera/screen
- 🎤 **Voice Monitoring**: Real-time conversation transcription and analysis
- 💡 **Strategic Guidance**: AI-powered negotiation recommendations
- 📊 **Market Intelligence**: Automated price research and comparison
- 🎯 **Dynamic Strategy**: Adaptive recommendations based on conversation flow
- 📈 **Outcome Analysis**: Comprehensive deal effectiveness metrics

### Technology Stack
- **Frontend**: Next.js 14+, TypeScript, React, TailwindCSS
- **Backend**: Python 3.11+, FastAPI, WebSockets
- **AI Engine**: Google Gemini Multimodal Live API
- **Deployment**: Google Cloud Run
- **Development**: Windows 11 (PowerShell)

---

## 📦 Package Contents

This Developer Handoff Package contains everything needed to build the application:

### Documentation Files
1. **ARCHITECTURE.md** - Complete system architecture, folder structure, data flows
2. **API_CONTRACTS.md** - WebSocket events, message schemas, data models
3. **AGENT_EXECUTION_PLAN.md** - Phased build approach with 8 phases
4. **.agentrules** - Strict coding rules and best practices
5. **MASTER_SYSTEM_PROMPT.txt** - Initialization prompt for coding agents
6. **README.md** - This file

### What You'll Build
```
ai-negotiation-copilot/
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── infrastructure/    # Deployment configs
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

---

## 🚀 Quick Start for Coding Agents

If you're an autonomous coding agent (OpenCode/OpenClaw/etc.), follow these steps:

### Step 1: Read Documentation
```
1. Read ARCHITECTURE.md completely
2. Read API_CONTRACTS.md completely
3. Read AGENT_EXECUTION_PLAN.md completely
4. Read .agentrules completely
5. Read MASTER_SYSTEM_PROMPT.txt completely
```

### Step 2: Initialize Your Context
Copy the contents of **MASTER_SYSTEM_PROMPT.txt** into your system prompt or context window.

### Step 3: Begin Execution
Start with **Phase 0** from AGENT_EXECUTION_PLAN.md and proceed sequentially through all 8 phases.

### Step 4: Verify Each Phase
After completing each phase, verify all functionality works on Windows before proceeding.

---

## 🛠️ Manual Setup (For Human Developers)

### Prerequisites
- Windows 11
- Python 3.11+
- Node.js 18+ LTS
- Git
- Google Cloud SDK
- Gemini API access

### Environment Setup

**1. Clone/Create Project**
```powershell
mkdir ai-negotiation-copilot
cd ai-negotiation-copilot
git init
```

**2. Set Up Backend**
```powershell
mkdir backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install fastapi uvicorn websockets python-dotenv google-generativeai pydantic pillow
```

**3. Set Up Frontend**
```powershell
cd ..\frontend
npx create-next-app@latest . --typescript --tailwind --app
npm install
```

**4. Configure Environment**
Create `backend/.env`:
```
GOOGLE_CLOUD_PROJECT=your-project-id
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash-exp
CORS_ORIGINS=["http://localhost:3000"]
```

**5. Start Development Servers**
```powershell
# Terminal 1 - Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

---

## 📋 Development Phases

The project is built in 8 sequential phases:

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| 0 | Project Initialization | Folder structure, dependencies |
| 1 | Backend Skeleton | FastAPI app, health checks |
| 2 | WebSocket Infrastructure | Bidirectional communication |
| 3 | Gemini Integration | Real AI API connection |
| 4 | Frontend Foundation | Next.js app, WebSocket client |
| 5 | Media Capture | Camera/mic access, streaming |
| 6 | Negotiation Intelligence | Context, market, strategy services |
| 7 | UI Polish & Testing | Complete UI, tests |
| 8 | Deployment | Docker, Cloud Run |

**See AGENT_EXECUTION_PLAN.md for detailed tasks and verification steps.**

---

## 🏗️ Architecture Overview

### Data Flow
```
User Browser
    ↓ (getUserMedia)
Camera/Microphone
    ↓ (WebSocket)
FastAPI Backend
    ↓ (Streaming)
Gemini Live API
    ↓ (Analysis)
Negotiation Engine
    ↓ (WebSocket)
Frontend UI Updates
```

### Key Components

**Frontend**
- `VideoCapture.tsx` - Camera/screen capture
- `AudioMonitor.tsx` - Microphone input
- `NegotiationDashboard.tsx` - Strategy display
- `RecommendationPanel.tsx` - AI suggestions
- `OutcomeSummary.tsx` - Final analysis

**Backend**
- `websocket.py` - WebSocket endpoint
- `gemini_client.py` - Gemini API integration
- `context_analyzer.py` - Vision analysis
- `market_analyzer.py` - Price research
- `strategy_generator.py` - Recommendation engine
- `negotiation_engine.py` - Orchestration

---

## 🔌 API Reference

### WebSocket Events

**Client → Server**
- `PRIVACY_CONSENT_GRANTED` - User grants audio monitoring permission
- `START_NEGOTIATION` - Begin new session
- `VISION_FRAME` - Send captured image
- `AUDIO_CHUNK` - Stream audio data
- `USER_MESSAGE` - Text message to AI
- `END_NEGOTIATION` - Finish session

**Server → Client**
- `CONNECTION_ESTABLISHED` - Connection confirmed
- `SESSION_STARTED` - Session initialized
- `CONTEXT_EXTRACTED` - Vision analysis results
- `STRATEGY_UPDATE` - New negotiation strategy
- `TRANSCRIPT_UPDATE` - Conversation transcription
- `AI_RESPONSE` - AI recommendation
- `OUTCOME_SUMMARY` - Final deal analysis

**See API_CONTRACTS.md for complete schemas and examples.**

---

## 🧪 Testing

### Backend Tests
```powershell
cd backend
.\venv\Scripts\activate
pytest tests/ -v
```

### Frontend Tests
```powershell
cd frontend
npm test
```

### Manual Testing
1. Start both servers
2. Open http://localhost:3000
3. Grant camera/microphone permissions
4. Point camera at price tag or product
5. Speak to test audio capture
6. Verify AI responses appear

---

## 🚢 Deployment

### Build Docker Images
```powershell
docker build -t negotiation-backend ./backend
docker build -t negotiation-frontend ./frontend
```

### Deploy to Cloud Run
```powershell
gcloud run deploy negotiation-backend --source ./backend --region us-central1
gcloud run deploy negotiation-frontend --source ./frontend --region us-central1
```

### Environment Variables (Production)
Set in Cloud Run:
- `GOOGLE_CLOUD_PROJECT`
- `GEMINI_API_KEY`
- `CORS_ORIGINS` (frontend URL)

---

## 📖 Documentation Structure

### For Understanding
- **README.md** (this file) - Overview and quick start
- **ARCHITECTURE.md** - System design and data flows

### For Implementation
- **API_CONTRACTS.md** - Message schemas and contracts
- **AGENT_EXECUTION_PLAN.md** - Step-by-step build guide
- **.agentrules** - Coding standards and rules

### For Agents
- **MASTER_SYSTEM_PROMPT.txt** - Complete initialization prompt

---

## ⚠️ Critical Rules

### ALWAYS
- ✅ Use PowerShell commands (Windows environment)
- ✅ Use official Gemini SDK (no mocking)
- ✅ Handle errors gracefully
- ✅ Test on Windows after each change
- ✅ Verify phase completion before proceeding

### NEVER
- ❌ Use bash/sh commands
- ❌ Mock the Gemini API
- ❌ Skip error handling
- ❌ Commit secrets to git
- ❌ Skip phase verification

**See .agentrules for complete list.**

---

## 🎯 Success Criteria

The project is complete when:
- ✅ All 8 phases finished and verified
- ✅ End-to-end negotiation flow works
- ✅ Real Gemini API integration functional
- ✅ Deployed to Google Cloud Run
- ✅ All documentation complete
- ✅ Ready for hackathon submission

---

## 🏆 Gemini Live Agent Challenge

This project is built for the **Gemini Live Agent Challenge** in the **Live Agent** category.

### Judging Criteria
- **Innovation & Multimodal UX (40%)**: Beyond text-box interaction, seamless multimodal experience
- **Technical Implementation (30%)**: Google Cloud native, robust architecture, error handling
- **Demo & Presentation (30%)**: Clear problem/solution, working software, architecture proof

### Submission Requirements
- ✅ Uses Gemini Live API
- ✅ Hosted on Google Cloud
- ✅ Handles barge-in naturally
- ✅ Public code repository
- ✅ Demo video (max 4 minutes)
- ✅ Architecture diagram
- ✅ Proof of GCP deployment

---

## 📞 Support

### For Coding Agents
- Refer to MASTER_SYSTEM_PROMPT.txt for complete instructions
- Follow AGENT_EXECUTION_PLAN.md phase by phase
- Consult .agentrules when making decisions

### For Human Developers
- Review ARCHITECTURE.md for system design
- Check API_CONTRACTS.md for integration details
- Follow AGENT_EXECUTION_PLAN.md for build sequence

---

## 📄 License

This project is built for the Gemini Live Agent Challenge. All intellectual property rights remain with the developer as per contest rules.

---

## 🚀 Ready to Build?

**For Coding Agents**: Start by reading MASTER_SYSTEM_PROMPT.txt

**For Human Developers**: Begin with Phase 0 in AGENT_EXECUTION_PLAN.md

**Good luck building an amazing AI Negotiation Copilot!** 🎉
