---
phase: 03-audio-pipeline
researched: 2026-03-07T10:38:00Z
---

## Research Summary

The audio pipeline is the most critical and complex portion of the AI Negotiation Copilot architecture. Because the Gemini Live API strictly requires raw 16-bit PCM audio at 16kHz for input and streams 24kHz PCM for playback, standard browser `MediaRecorder` APIs (which natively generate WebM/Opus) are incompatible and will result in silent rejections. Therefore, a custom low-level `AudioWorklet` implementation is required to interact with `AudioContext`.

## Technology Recommendations

- **Capture & Playback APIs:** Use the uncompressed Web Audio API, specifically `AudioWorklet`, to intercept microphone chunks and feed speaker outputs directly.
- **WebSocket Transport:** Use binary WebSocket frames (`ArrayBuffer`) exclusively for audio data passing to bypass the 33% payload bloat and latency of Base64/JSON encoding.
- **Sample Rates:** 
  - Capture Context MUST be forced to `sampleRate: 16000`.
  - Playback Context MUST be forced to `sampleRate: 24000`.

## Architecture Recommendations

- **Worklet Separation:** Maintain two distinct processors: `pcm-processor.js` for intercepting Float32 arrays from the mic and packing them into Int16 buffers, and `pcm-playback-processor.js` for consuming Int16 buffers and converting them back to Float32.
- **TypeScript Manager:** Implement a unified `AudioWorkletManager` class to encapsulate all context lifecycles, node connections, and stream cleanups.

## Implementation Considerations

- **URL Resolving:** The Worklet JS files MUST reside in `frontend/public/worklets/`. Modern bundlers like Next.js/Webpack will fail to correctly process `audioWorklet.addModule()` if passed as a module import.
- **Playback Queueing:** A queue with overflow protection inside the playback worklet is necessary to prevent memory constraints or crashes if the frontend receives faster-than-realtime audio bursts from Gemini.

## Codebase Patterns

- Ensure the frontend `websocket.ts` uses type-checking (`event.data instanceof ArrayBuffer` or `Blob`) in the `onmessage` handler to cleanly separate the binary audio stream and JSON control frames (like `STRATEGY_UPDATE`).

## Potential Pitfalls

- Forgetting to downsample the user's microphone. If the browser captures at 44.1kHz or 48kHz, the raw PCM will be rejected.
- Leaking AudioContexts. The `cleanup()` methodology must aggressively close contexts and stop media tracks to release the microphone hardware completely.

## Integration Notes

- No backend changes are required for the audio *source*, but the Python FastAPI backend will need to simply wrap the binary frames in `types.Blob(mime_type="audio/pcm;rate=16000")` before forwarding to the `google-genai` client.

## Open Questions

- None. The architecture and requirements dictating the audio flow are rigid and comprehensively designed to accommodate Gemini Live.
