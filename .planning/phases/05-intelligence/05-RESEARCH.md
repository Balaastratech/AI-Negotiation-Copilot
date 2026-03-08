# Phase 5: Intelligence Integration - Research & Architecture Rules

**Status: Approved for Implementation**
**Focus:** Live streaming data parsing, real-time interruptions, and session limits

---

## 1. The Strategy Parsing Problem
**Challenge:** Gemini Live streaming responses will mix spoken text intended for the user's ears with structured JSON intended for our UI strategy board.
**Solution Context:** `SYSTEM_PROMPT.md` instructs the model to wrap strategy updates in `<strategy>...</strategy>` tags. 

### Implementation Rules:
- **Parser Design:** Due to chunked streaming, a JSON block may arrive across multiple WebSocket frames. The `negotiation_engine.py` MUST buffer text until the `</strategy>` tag arrives or use regex over the full text output provided by the SDK's `part.text`.
- **SDK Capability Check:** Fortunately, the `google-genai` SDK handles re-assembling chunks into `part.text` when `sc.model_turn` events occur, so we only need to parse complete blocks using `re.compile(r'<strategy>(.*?)</strategy>', re.DOTALL)`.
- **Fault Tolerance:** If `json.loads` fails on a malformed strategy string, discard it. It is better to rely on the previous strategy than crash the active negotiation session. 

---

## 2. Audio Interruption (Barge-In)
**Challenge:** When Gemini is speaking, the user may interrupt by talking. Gemini detects this server-side and stops generating audio, but the frontend may still have 2-3 seconds of PCM audio buffered in the `AudioWorkletManager` queue.
**Solution Context:** `sc.interrupted` flag in the Gemini response stream.

### Implementation Rules:
- **Backend Flow:** When `response.server_content.interrupted` is true, the `receive_responses` loop immediately sends an `AUDIO_INTERRUPTED` JSON frame to the frontend over WebSocket.
- **Frontend Flow:** The `useNegotiation` hook traps `AUDIO_INTERRUPTED` and synchronously calls `audioManager.clearQueue()` to flush all pending buffers, instantly silencing the AI to let the user speak.

---

## 3. The 10-Minute Hard Limit
**Challenge:** Gemini Live API forcefully disconnects any session that reaches 10 minutes. Complex negotiations frequently take 15-20 minutes.
**Solution Context:** Pre-emptively trigger a "Soft Handoff" at the 9-minute (540 seconds) mark.

### Implementation Rules:
- **Handoff Mechanism:** A background `asyncio` task (`monitor_session_lifetime`) runs in `negotiation_engine.py`. When the timer expires, the backend:
   1. Collects the last 10 messages from the `NegotiationSession.transcript` and the most recent `Strategy` block.
   2. Generates an injected text block (`CONTINUATION CONTEXT`).
   3. Closes the existing Gemini Live WebSocket connection and opens a new one, passing the context summary entirely invisible to the user.
- **Frontend Awareness:** The connection between the *User Browser* and *FastAPI Backend* stays active the entire time. No UI interruption occurs. This allows infinite negotiation lengths.

---

## Conclusion
The architectural mechanisms for Phase 5 are fully defined. The dependencies between Python regex parsing, async background session monitors, and React-managed AudioWorklet queues are technically robust. We are cleared to execute Phase 5.
