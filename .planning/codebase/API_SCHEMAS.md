# API Schemas — Exact WebSocket Message Payloads

**Status: AUTHORITATIVE — Frontend and Backend must match this exactly**
**Last Updated: 2026-03-06**

---

## Message Frame Types

There are TWO distinct WebSocket frame types. The code must handle both:

| Frame Type | Direction | Content | How to Detect |
|---|---|---|---|
| **Text frame** | Both directions | JSON string | `event.data` is `string` |
| **Binary frame** | Frontend → Backend | Raw PCM audio (Int16, 16kHz) | `event.data` is `ArrayBuffer` or `Blob` |
| **Binary frame** | Backend → Frontend | Raw PCM audio (Int16, 24kHz) | `websocket.send_bytes()` |

---

## Client → Server Messages (Text Frames / JSON)

### `PRIVACY_CONSENT_GRANTED`
```json
{
  "type": "PRIVACY_CONSENT_GRANTED",
  "payload": {
    "version": "1.0",
    "mode": "live"
  }
}
```
**Fields:**
- `version`: string — consent document version (always `"1.0"` for now)
- `mode`: `"live"` | `"roleplay"` — live captures real audio; roleplay is demo mode

**Triggers:** State `IDLE → CONSENTED`

---

### `START_NEGOTIATION`
```json
{
  "type": "START_NEGOTIATION",
  "payload": {
    "context": "I am buying a used laptop at a market. The seller is asking $500."
  }
}
```
**Fields:**
- `context`: string — user-provided description of the negotiation situation (max 2000 chars)

**Triggers:** State `CONSENTED → ACTIVE`, opens Gemini Live session

---

### `VISION_FRAME`
```json
{
  "type": "VISION_FRAME",
  "payload": {
    "image": "base64encodedJPEGstring...",
    "timestamp": 1709700000000
  }
}
```
**Fields:**
- `image`: string — base64-encoded JPEG (max 500KB after encoding, ~375KB raw)
- `timestamp`: number — Unix milliseconds when frame was captured

**Rate:** 1 frame per second maximum
**Only valid in:** `ACTIVE` state

---

### `END_NEGOTIATION`
```json
{
  "type": "END_NEGOTIATION",
  "payload": {
    "final_price": 420.00,
    "initial_price": 500.00
  }
}
```
**Fields:**
- `final_price`: number | null — agreed final price (null if no deal reached)
- `initial_price`: number | null — original asking price from seller (null if unknown)

**Triggers:** State `ACTIVE → ENDING → IDLE`

---

### `AUDIO_CHUNK` (Binary WebSocket Frame — NOT JSON)
```
[raw bytes: Int16 PCM, 16kHz, mono, little-endian]
```
**This is NOT a JSON message.** It is a raw binary WebSocket frame.
- Sent directly: `websocket.send(int16Array.buffer)`
- Backend receives as: `message["bytes"]` in FastAPI WebSocket handler
- Size: ~8KB per chunk (4096 Int16 samples × 2 bytes)

---

## Server → Client Messages (Text Frames / JSON)

### `CONNECTION_ESTABLISHED`
```json
{
  "type": "CONNECTION_ESTABLISHED",
  "payload": {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "server_time": 1709700000000
  }
}
```
Sent immediately on WebSocket connection acceptance.

---

### `CONSENT_ACKNOWLEDGED`
```json
{
  "type": "CONSENT_ACKNOWLEDGED",
  "payload": {
    "mode": "live",
    "recording_active": true
  }
}
```

---

### `SESSION_STARTED`
```json
{
  "type": "SESSION_STARTED",
  "payload": {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "model": "gemini-2.5-flash-native-audio-preview-12-2025",
    "features": {
      "audio": true,
      "vision": true,
      "web_search": true
    }
  }
}
```
Sent when Gemini Live session is successfully opened.

---

### `TRANSCRIPT_UPDATE`
```json
{
  "type": "TRANSCRIPT_UPDATE",
  "payload": {
    "id": "txn_001",
    "speaker": "user",
    "text": "He says the best he can do is $450.",
    "timestamp": 1709700015000
  }
}
```
**Fields:**
- `id`: string — unique transcript entry ID (`txn_` prefix + sequence number)
- `speaker`: `"user"` | `"counterparty"` | `"ai"` — who said it
- `text`: string — transcribed speech
- `timestamp`: number — Unix milliseconds

---

### `STRATEGY_UPDATE`
```json
{
  "type": "STRATEGY_UPDATE",
  "payload": {
    "target_price": 380.00,
    "current_offer": 450.00,
    "recommended_response": "Counter with $390. Point out the battery health is at 74% and cite the average market price of $400 for this model.",
    "key_points": [
      "Battery health: 74% (below average)",
      "Market average: ~$400 for this model/year",
      "Seller has been asking for 2 weeks (motivation to sell)"
    ],
    "approach_type": "collaborative",
    "confidence": 0.78,
    "walkaway_threshold": 430.00,
    "web_search_used": true,
    "search_sources": ["GSMArena", "eBay completed listings"]
  }
}
```
**Fields:**
- `target_price`: number | null — AI's recommended price to aim for
- `current_offer`: number | null — seller's current position
- `recommended_response`: string — exact words to say next
- `key_points`: string[] — talking points to use
- `approach_type`: `"aggressive"` | `"collaborative"` | `"walkaway"` 
- `confidence`: number — 0.0 to 1.0, AI's confidence in the strategy
- `walkaway_threshold`: number | null — price above which to walk away
- `web_search_used`: boolean — whether live search was used
- `search_sources`: string[] — sources consulted (empty if no search)

---

### `AI_RESPONSE`
```json
{
  "type": "AI_RESPONSE",
  "payload": {
    "text": "Based on what I can see, this laptop has significant screen scratches...",
    "response_type": "analysis",
    "timestamp": 1709700020000
  }
}
```
**Fields:**
- `text`: string — Gemini's full text response
- `response_type`: `"analysis"` | `"coaching"` | `"alert"` | `"summary"`
- `timestamp`: number

---

### `OUTCOME_SUMMARY`
```json
{
  "type": "OUTCOME_SUMMARY",
  "payload": {
    "deal_reached": true,
    "initial_price": 500.00,
    "final_price": 395.00,
    "savings": 105.00,
    "savings_percentage": 21.0,
    "market_value": 400.00,
    "vs_market": -5.00,
    "negotiation_duration_seconds": 387,
    "key_moves": [
      "Highlighted battery health issue",
      "Used market price anchor",
      "Offered immediate payment as sweetener"
    ],
    "effectiveness_score": 0.82,
    "transcript_summary": "Started at $500, countered at $390, settled at $395 after 6 minutes."
  }
}
```

---

### `AUDIO_INTERRUPTED`
```json
{
  "type": "AUDIO_INTERRUPTED",
  "payload": {}
}
```
Signal that Gemini detected a barge-in. Frontend must clear its audio playback queue immediately.

---

### `SESSION_RECONNECTING`
```json
{
  "type": "SESSION_RECONNECTING",
  "payload": {
    "reason": "gemini_session_dropped",
    "attempt": 1,
    "max_attempts": 3
  }
}
```
**Decision: AUTO-RECONNECT (Option A, locked 2026-03-06)**

Sent when the backend detects a dropped Gemini Live WebSocket and is silently re-opening it.
The frontend MUST NOT show an error dialog or require user action.
The frontend SHOULD show a subtle, non-blocking status indicator (e.g. a spinner in the strategy panel header).
Once the new session is open and streaming resumes, the backend sends `SESSION_STARTED` again with the new session info.

**Fields:**
- `reason`: `"gemini_session_dropped"` | `"session_timeout"` | `"model_fallback"` — what triggered the reconnect
- `attempt`: number — which reconnect attempt this is (1-indexed)
- `max_attempts`: number — total attempts before giving up (always `3`)

**Failure path:** If all `max_attempts` are exhausted, backend sends `AI_DEGRADED` and continues in text-only strategy mode.

---

### `AI_DEGRADED`
```json
{
  "type": "AI_DEGRADED",
  "payload": {
    "message": "AI connection interrupted. Vision features may be limited.",
    "features_available": ["text_strategy", "audio"]
  }
}
```
**Fields:**
- `message`: string — human-readable status
- `features_available`: string[] — what still works

---

### `ERROR`
```json
{
  "type": "ERROR",
  "payload": {
    "code": "NOT_CONSENTED",
    "message": "Please accept privacy terms first."
  }
}
```
See STATE_MACHINE.md for complete error code catalog.

---

## Server → Client Messages (Binary Frames)

```
[raw bytes: Int16 PCM, 24kHz, mono, little-endian]
```
Gemini's spoken audio response. Frontend must detect this as `ArrayBuffer`/`Blob` and feed to playback AudioWorklet.

---

## TypeScript Type Definitions

These are the EXACT types for `frontend/lib/types.ts`. Do not invent alternatives.

```typescript
// frontend/lib/types.ts

export type ClientMessageType =
  | 'PRIVACY_CONSENT_GRANTED'
  | 'START_NEGOTIATION'
  | 'VISION_FRAME'
  | 'END_NEGOTIATION';
// Note: AUDIO_CHUNK is a binary frame, NOT a typed JSON message

export type ServerMessageType =
  | 'CONNECTION_ESTABLISHED'
  | 'CONSENT_ACKNOWLEDGED'
  | 'SESSION_STARTED'
  | 'TRANSCRIPT_UPDATE'
  | 'STRATEGY_UPDATE'
  | 'AI_RESPONSE'
  | 'OUTCOME_SUMMARY'
  | 'AUDIO_INTERRUPTED'
  | 'SESSION_RECONNECTING'    // backend is silently re-opening Gemini session (Topic 4)
  | 'AI_DEGRADED'
  | 'ERROR';

export interface WebSocketMessage {
  type: ServerMessageType;
  payload: unknown;
}

export interface TranscriptEntry {
  id: string;
  speaker: 'user' | 'counterparty' | 'ai';
  text: string;
  timestamp: number;
}

export interface Strategy {
  target_price: number | null;
  current_offer: number | null;
  recommended_response: string;
  key_points: string[];
  approach_type: 'aggressive' | 'collaborative' | 'walkaway';
  confidence: number;
  walkaway_threshold: number | null;
  web_search_used: boolean;
  search_sources: string[];
}

export interface OutcomeSummary {
  deal_reached: boolean;
  initial_price: number | null;
  final_price: number | null;
  savings: number | null;
  savings_percentage: number | null;
  market_value: number | null;
  vs_market: number | null;
  negotiation_duration_seconds: number;
  key_moves: string[];
  effectiveness_score: number;
  transcript_summary: string;
}

export interface NegotiationState {
  sessionId: string | null;
  isConnected: boolean;
  isNegotiating: boolean;
  consentGiven: boolean;
  transcript: TranscriptEntry[];
  strategy: Strategy | null;
  outcome: OutcomeSummary | null;
  isAudioActive: boolean;
  isVisionActive: boolean;
  aiDegraded: boolean;
  error: string | null;
}

export const INITIAL_NEGOTIATION_STATE: NegotiationState = {
  sessionId: null,
  isConnected: false,
  isNegotiating: false,
  consentGiven: false,
  transcript: [],
  strategy: null,
  outcome: null,
  isAudioActive: false,
  isVisionActive: false,
  aiDegraded: false,
  error: null,
};
```

---

## Mock Data for Frontend Development

Use these during Phase 4 (UI development) before the backend is ready.

```typescript
// frontend/lib/mock-data.ts

export const MOCK_STRATEGY: Strategy = {
  target_price: 380,
  current_offer: 450,
  recommended_response: "Counter with $385. Point out the battery is at 74% health and the average eBay price is $380-400 for this model.",
  key_points: [
    "Battery health: 74% (below average)",
    "eBay completed listings: $370-410",
    "Seller motivation: listed for 2 weeks"
  ],
  approach_type: "collaborative",
  confidence: 0.78,
  walkaway_threshold: 430,
  web_search_used: true,
  search_sources: ["eBay completed listings", "GSMArena"]
};

export const MOCK_TRANSCRIPT: TranscriptEntry[] = [
  { id: "txn_001", speaker: "user", text: "I'm interested in the laptop. What's your best price?", timestamp: Date.now() - 60000 },
  { id: "txn_002", speaker: "counterparty", text: "I'm asking $500, it's in great condition.", timestamp: Date.now() - 50000 },
  { id: "txn_003", speaker: "ai", text: "I can see the laptop from here. The screen has some scratches and the battery indicator shows 74%.", timestamp: Date.now() - 45000 },
];
```

---

*API schemas: 2026-03-06*
