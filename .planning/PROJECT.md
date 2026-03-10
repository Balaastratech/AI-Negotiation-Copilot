# AI Negotiation Copilot Improvements

## What This Is

A real-time AI negotiation advisor that listens to conversations between users and counterparties, providing strategic advice on demand through a button-triggered system. The immediate focus is improving the current AI's advice quality.

## Core Value

Users get contextual, data-backed negotiation advice that helps them negotiate better deals, rather than generic random suggestions.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Phase 1: Enhanced Master Prompt with detailed AI instructions
- [ ] Phase 2: Adaptive Context-Aware Query system
- [ ] Phase 3: Web Search Integration for market research
- [ ] Phase 4: Testing & Refinement

### Out of Scope

- Voice fingerprinting for speaker diarization — defer to future (WHAT_WE_ARE_BUILDING.md vision)
- Video stream processing — defer to future
- Dual live session architecture — defer to future

## Context

The project has an existing codebase with:
- Backend: Python/FastAPI with Gemini Live API integration
- Frontend: TypeScript/React with WebSocket connections
- Current issues: AI gives random unrealistic advice, lacks market research capability

Key documents:
- `WHAT_WE_ARE_BUILDING.md` — Long-term vision (Gemini Live redesign)
- `NEGOTIATION_AI_IMPROVEMENT_PLAN.md` — Immediate improvement plan with 4 phases

## Constraints

- **Tech Stack**: Python FastAPI backend, React frontend, Gemini Live API
- **Timeline**: Hackathon demo focused
- **Dependencies**: Google Gemini API, WebSocket connections

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Phase 1 first | Foundation for all subsequent phases | — Pending |
| Hybrid context (Phase 2) | Balance history + recent precision | — Pending |
| Backend pre-search (Phase 3) | Simpler implementation | — Pending |
| AI decides when to research | More efficient, intent-driven | — Pending |

---
*Last updated: 2026-03-10 after project initialization*
