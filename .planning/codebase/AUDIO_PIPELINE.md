# Audio Pipeline Architecture

**Status: CRITICAL — Read before writing any audio-related code**
**Last Updated: 2026-03-06**

---

## The Core Problem

The browser's `MediaRecorder` API produces `audio/webm;codecs=opus`. The Gemini Live API **rejects this format entirely**. It requires:

- **Input (browser → Gemini):** Raw 16-bit PCM, 16kHz, mono, little-endian
- **Output (Gemini → browser):** Raw 16-bit PCM, 24kHz, mono, little-endian

`MediaRecorder` must NOT be used for audio capture. The correct approach is `AudioWorklet` + `AudioContext` at a forced 16kHz sample rate.

---

## Complete Audio Data Flow

```
[User's Microphone]
        ↓
getUserMedia({ audio: { channelCount: 1 } })
        ↓
AudioContext({ sampleRate: 16000 })   ← FORCES 16kHz capture
        ↓
AudioWorklet: pcm-processor.js         ← runs on dedicated thread
  - receives Float32 samples (128 samples per call)
  - converts Float32 → Int16 PCM
  - postMessage(Int16Array) to main thread
        ↓
Main thread: websocket.send(int16Array.buffer)   ← binary WebSocket frame (NOT JSON)
        ↓
[Backend FastAPI WebSocket]
  - receives raw bytes
  - wraps in Gemini types.Blob with mime_type="audio/pcm;rate=16000"
  - session.send_realtime_input(audio=blob)
        ↓
[Gemini Live API Session]  ← active persistent session
        ↓ (response)
Backend receives session response
  - extracts audio PCM data (24kHz)
  - sends as binary WebSocket frame back to frontend
        ↓
[Frontend Main Thread]
  - receives binary frame
  - feeds into playback AudioWorklet
        ↓
AudioWorklet: pcm-playback-processor.js
  - queues PCM chunks
  - outputs at 24kHz
        ↓
[User's Speaker / Headphones]
```

---

## File Locations

```
frontend/
└── public/
    └── worklets/
        ├── pcm-processor.js        ← CAPTURE worklet (must be in public/)
        └── pcm-playback-processor.js ← PLAYBACK worklet (must be in public/)

frontend/
└── lib/
    └── audio-worklet-manager.ts    ← TypeScript manager class
```

**WHY `public/`?** AudioWorklet requires a URL path (`audioWorklet.addModule('/worklets/pcm-processor.js')`). Files inside `public/` are served directly. Bundled imports do NOT work with `addModule`.

---

## File 1: `frontend/public/worklets/pcm-processor.js`

```javascript
/**
 * PCM Capture Processor
 * Runs on dedicated AudioWorklet thread.
 * Converts Float32 microphone input to Int16 PCM at 16kHz.
 * Sends raw Int16 ArrayBuffer to main thread via postMessage.
 */
class PCMCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._bufferSize = 4096; // ~256ms at 16kHz — balance latency vs. efficiency
  }

  process(inputs, outputs, parameters) {
    if (inputs.length === 0 || inputs[0].length === 0) return true;

    const input = inputs[0][0]; // mono channel, Float32Array (128 samples)

    for (let i = 0; i < input.length; i++) {
      // Convert Float32 [-1.0, 1.0] → Int16 [-32768, 32767]
      const s = Math.max(-1, Math.min(1, input[i]));
      this._buffer.push(s < 0 ? s * 0x8000 : s * 0x7fff);
    }

    if (this._buffer.length >= this._bufferSize) {
      const int16 = new Int16Array(this._buffer.splice(0, this._bufferSize));
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }

    return true; // keep processor alive
  }
}

registerProcessor('pcm-capture-processor', PCMCaptureProcessor);
```

---

## File 2: `frontend/public/worklets/pcm-playback-processor.js`

```javascript
/**
 * PCM Playback Processor
 * Runs on dedicated AudioWorklet thread.
 * Receives Int16 PCM chunks from main thread and plays them at 24kHz.
 * Implements a queue with overflow protection to prevent memory leaks.
 */
class PCMPlaybackProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._queue = [];
    this._maxQueueBytes = 24000 * 2 * 3; // max 3 seconds of audio buffered

    this.port.onmessage = (event) => {
      const totalQueued = this._queue.reduce((sum, buf) => sum + buf.length, 0);
      if (totalQueued * 2 > this._maxQueueBytes) {
        // Drop oldest chunk to prevent unbounded queue growth
        this._queue.shift();
      }
      this._queue.push(new Int16Array(event.data));
    };
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0][0]; // mono channel
    let offset = 0;

    while (offset < output.length && this._queue.length > 0) {
      const chunk = this._queue[0];
      const remaining = output.length - offset;
      const toCopy = Math.min(chunk.length, remaining);

      for (let i = 0; i < toCopy; i++) {
        // Convert Int16 → Float32
        output[offset + i] = chunk[i] / (chunk[i] < 0 ? 0x8000 : 0x7fff);
      }

      if (toCopy === chunk.length) {
        this._queue.shift();
      } else {
        this._queue[0] = chunk.subarray(toCopy);
      }

      offset += toCopy;
    }

    // Fill remaining output with silence if queue is empty
    for (let i = offset; i < output.length; i++) {
      output[i] = 0;
    }

    return true;
  }
}

registerProcessor('pcm-playback-processor', PCMPlaybackProcessor);
```

---

## File 3: `frontend/lib/audio-worklet-manager.ts`

```typescript
/**
 * AudioWorkletManager
 * Manages capture and playback AudioWorklets for Gemini Live API.
 * Replaces MediaStreamManager's audio functions entirely.
 * 
 * IMPORTANT: Call cleanup() on component unmount or session end.
 */
export class AudioWorkletManager {
  private captureContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private captureWorkletNode: AudioWorkletNode | null = null;
  private playbackWorkletNode: AudioWorkletNode | null = null;
  private micStream: MediaStream | null = null;
  private onAudioChunk: ((buffer: ArrayBuffer) => void) | null = null;

  /**
   * Start microphone capture.
   * Returns a stream of Int16 PCM ArrayBuffers at 16kHz.
   * Each chunk is ~4096 samples (~256ms of audio).
   */
  async startCapture(onChunk: (buffer: ArrayBuffer) => void): Promise<void> {
    this.onAudioChunk = onChunk;

    // AudioContext at 16kHz forces browser to downsample from 44.1/48kHz
    this.captureContext = new AudioContext({ sampleRate: 16000 });

    await this.captureContext.audioWorklet.addModule('/worklets/pcm-processor.js');

    this.micStream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      video: false,
    });

    const source = this.captureContext.createMediaStreamSource(this.micStream);
    this.captureWorkletNode = new AudioWorkletNode(
      this.captureContext,
      'pcm-capture-processor'
    );

    this.captureWorkletNode.port.onmessage = (event: MessageEvent) => {
      if (this.onAudioChunk) {
        this.onAudioChunk(event.data as ArrayBuffer);
      }
    };

    source.connect(this.captureWorkletNode);
    this.captureWorkletNode.connect(this.captureContext.destination);
  }

  /**
   * Initialize audio playback for Gemini responses.
   * Call this before the session starts, not after first audio arrives.
   */
  async initPlayback(): Promise<void> {
    // Playback context at 24kHz to match Gemini output
    this.playbackContext = new AudioContext({ sampleRate: 24000 });
    await this.playbackContext.audioWorklet.addModule('/worklets/pcm-playback-processor.js');

    this.playbackWorkletNode = new AudioWorkletNode(
      this.playbackContext,
      'pcm-playback-processor'
    );

    this.playbackWorkletNode.connect(this.playbackContext.destination);
  }

  /**
   * Feed a PCM chunk received from Gemini into the playback worklet.
   * chunk: ArrayBuffer of Int16 PCM at 24kHz
   */
  playChunk(chunk: ArrayBuffer): void {
    if (!this.playbackWorkletNode) return;
    // Transfer ownership of buffer to worklet thread (zero-copy)
    this.playbackWorkletNode.port.postMessage(chunk, [chunk]);
  }

  /**
   * Stop mic capture without stopping playback.
   */
  stopCapture(): void {
    this.micStream?.getTracks().forEach(t => t.stop());
    this.captureWorkletNode?.disconnect();
    this.captureContext?.close();
    this.micStream = null;
    this.captureWorkletNode = null;
    this.captureContext = null;
  }

  /**
   * Full cleanup — call on session end or component unmount.
   */
  cleanup(): void {
    this.stopCapture();
    this.playbackWorkletNode?.disconnect();
    this.playbackContext?.close();
    this.playbackWorkletNode = null;
    this.playbackContext = null;
    this.onAudioChunk = null;
  }

  get isCapturing(): boolean {
    return this.captureContext !== null && this.captureContext.state === 'running';
  }
}
```

---

## Backend Audio Bridge Pattern

### Receiving binary audio from frontend

```python
# backend/app/api/websocket.py

async def handle_audio_chunk(
    websocket: WebSocket,
    session_id: str,
    raw_bytes: bytes,
    live_session  # google.genai live session handle
) -> None:
    """
    Forward raw PCM bytes from frontend to Gemini Live session.
    
    Frontend sends: binary WebSocket frame (Int16 PCM, 16kHz, mono)
    Gemini expects: types.Blob with mime_type="audio/pcm;rate=16000"
    """
    try:
        blob = types.Blob(
            data=raw_bytes,
            mime_type="audio/pcm;rate=16000"
        )
        await live_session.send_realtime_input(audio=blob)
    except Exception as e:
        logger.error(f"Audio forward error [{session_id}]: {e}")
        # Do NOT disconnect — audio errors are transient. Log and continue.
```

### Receiving PCM from Gemini and sending to frontend

```python
async def handle_gemini_response(
    websocket: WebSocket,
    session_id: str,
    live_session
) -> None:
    """
    Receive responses from Gemini and route them to frontend.
    
    Audio responses → binary WebSocket frame (Int16 PCM, 24kHz)
    Text responses  → JSON WebSocket message (STRATEGY_UPDATE, TRANSCRIPT_UPDATE)
    """
    async for response in live_session.receive():
        
        # Handle audio output (spoken guidance)
        if response.server_content and response.server_content.model_turn:
            for part in response.server_content.model_turn.parts:
                if part.inline_data and part.inline_data.mime_type.startswith('audio/pcm'):
                    # Send raw PCM bytes as binary frame
                    await websocket.send_bytes(
                        base64.b64decode(part.inline_data.data)
                    )
        
        # Handle text output (strategy JSON)
        if response.server_content and response.server_content.model_turn:
            for part in response.server_content.model_turn.parts:
                if part.text:
                    await _handle_text_response(websocket, session_id, part.text)
        
        # Handle input transcription
        if response.server_content and response.server_content.input_transcription:
            transcript_text = response.server_content.input_transcription.text
            if transcript_text:
                await websocket.send_json({
                    "type": "TRANSCRIPT_UPDATE",
                    "payload": {
                        "speaker": "user",
                        "text": transcript_text,
                        "timestamp": int(time.time() * 1000)
                    }
                })
        
        # Handle barge-in / interruption
        if response.server_content and response.server_content.interrupted:
            # Clear pending audio on frontend
            await websocket.send_json({
                "type": "AUDIO_INTERRUPTED",
                "payload": {}
            })
```

---

## Frontend WebSocket Frame Types

The frontend WebSocket client must handle **two distinct frame types**:

```typescript
// frontend/lib/websocket.ts

ws.onmessage = (event: MessageEvent) => {
  if (event.data instanceof ArrayBuffer || event.data instanceof Blob) {
    // BINARY frame = PCM audio from Gemini (24kHz Int16)
    event.data instanceof Blob
      ? event.data.arrayBuffer().then(buf => audioManager.playChunk(buf))
      : audioManager.playChunk(event.data);
  } else {
    // TEXT frame = JSON control message
    const message = JSON.parse(event.data as string);
    handleControlMessage(message);
  }
};

// Sending audio: ALWAYS binary, never JSON
function sendAudioChunk(pcmBuffer: ArrayBuffer): void {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(pcmBuffer); // binary frame
  }
}

// Sending control messages: ALWAYS JSON text frame
function sendControl(type: string, payload: unknown): void {
  ws.send(JSON.stringify({ type, payload }));
}
```

---

## Critical Constraints (Do Not Violate)

| Constraint | Reason |
|---|---|
| AudioContext sampleRate MUST be 16000 for capture | Gemini rejects other rates silently |
| AudioContext sampleRate MUST be 24000 for playback | Gemini outputs 24kHz; wrong rate = chipmunk effect |
| Audio frames MUST be binary WebSocket frames | JSON + base64 adds 33% overhead and latency |
| `pcm-processor.js` MUST be in `public/worklets/` | `addModule()` requires a URL, not a bundled import |
| MediaRecorder MUST NOT be used for audio-to-Gemini | WebM/Opus format is rejected by Gemini Live API |
| Playback queue MUST have overflow protection | Without it, 30+ seconds of audio causes memory crash |

---

## Latency Budget

| Stage | Target | Notes |
|---|---|---|
| AudioWorklet chunk size (128 samples) | ~8ms | Non-configurable by default |
| Buffer before sending (4096 samples) | ~256ms | Balance vs. latency |
| WebSocket transit (LAN/WiFi) | ~5-20ms | Binary vs JSON saves ~10ms |
| Gemini Live API processing | ~200-800ms | Model-dependent |
| Playback buffer | ~100-300ms | Queue-based smoothing |
| **Total round-trip** | **~600ms-1400ms** | Acceptable for negotiation copilot |

---

*Audio pipeline spec: 2026-03-06*
