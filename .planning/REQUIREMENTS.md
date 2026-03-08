# Project Requirements

**Project:** AI Negotiation Copilot  
**Created:** 2026-03-06

---

## Overview

AI Negotiation Copilot is a multimodal real-time negotiation assistant that observes negotiations through visual input, listens through voice input, and generates structured negotiation intelligence.

---

## Core Requirements

### Must Have (P0)
- Real-time audio capture and streaming via AudioWorklet
- Gemini Live API integration for multimodal interaction
- WebSocket communication between frontend and backend
- Video capture for visual context
- Strategy panel showing AI recommendations
- Transcript panel showing conversation
- Privacy consent flow
- Deployment to Google Cloud Run
- Deployment to Firebase Hosting

### Should Have (P1)
- Session resumption for long negotiations
- Outcome summary with savings calculation
- Multiple negotiation context presets

### Nice to Have (P2)
- Google Search grounding
- Multi-language support

---

## Constraints

- Must use Google Cloud (Cloud Run, Firebase Hosting)
- Must use Gemini Live API
- Must include privacy consent toggles
- User must remain in control (not autonomous agent)
- Maximum 4-minute demo video for submission

---

*Requirements captured: 2026-03-06*
