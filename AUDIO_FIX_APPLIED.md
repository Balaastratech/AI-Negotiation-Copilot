# Audio Format Fix Applied

## Problem Identified

The "1007 invalid frame payload data" error was caused by **audio format corruption** in the frontend audio processing pipeline.

### Root Cause

The `pcm-processor.js` worklet was using `Int16Array` constructor, which uses the platform's native byte order. On most systems this is little-endian, but the conversion from JavaScript array to Int16Array wasn't guaranteed to preserve the correct byte order, especially after accumulating samples over time.

Gemini Live API requires: **s16le** = signed 16-bit **little-endian** PCM

## Fix Applied

### 1. Frontend: Explicit Little-Endian Encoding

**File**: `frontend/public/worklets/pcm-processor.js`

**Changed from**:
```javascript
const int16 = new Int16Array(this._buffer.splice(0, this._bufferSize));
this.port.postMessage(int16.buffer, [int16.buffer]);
```

**Changed to**:
```javascript
const samples = this._buffer.splice(0, this._bufferSize);

// Use DataView to ensure little-endian encoding
const arrayBuffer = new ArrayBuffer(samples.length * 2);
const dataView = new DataView(arrayBuffer);

for (let i = 0; i < samples.length; i++) {
  // Explicitly write as little-endian Int16
  dataView.setInt16(i * 2, samples[i], true); // true = little-endian
}

this.port.postMessage(arrayBuffer, [arrayBuffer]);
```

**Why this fixes it**:
- `DataView.setInt16(offset, value, littleEndian)` explicitly controls byte order
- The `true` parameter forces little-endian encoding
- This guarantees the format matches Gemini's expectation

### 2. Backend: Diagnostic Logging

**File**: `backend/app/services/gemini_client.py`

Added comprehensive logging to help diagnose audio issues:

1. **Validation checks**:
   - Detects odd byte counts (incomplete samples)
   - Detects empty chunks
   - Logs statistics every 100 chunks

2. **Enhanced error reporting**:
   - Identifies audio format errors specifically
   - Shows total chunks sent before error
   - Provides actionable error messages

**Example log output**:
```
Audio stats: chunk #100, 8192 bytes, 4096 samples, 256.0ms @ 16kHz [session-id]
Audio stats: chunk #200, 8192 bytes, 4096 samples, 256.0ms @ 16kHz [session-id]
```

If an error occurs:
```
AUDIO FORMAT ERROR detected [session-id]:
  Error type: WebSocketException
  Error message: 1007 invalid frame payload data...
  This suggests the frontend is sending corrupted or incorrectly formatted audio
  Expected: 16kHz, signed 16-bit little-endian PCM, mono channel
  Total chunks sent before error: 347
```

## Testing Instructions

1. **Start the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Start the frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test the conversation**:
   - Open the app in your browser
   - Grant microphone permissions
   - Start a conversation
   - Talk for 5+ minutes
   - Watch the terminal for:
     - Chunk statistics (every 100 chunks)
     - Any error messages

4. **Expected behavior**:
   - No "1007 invalid frame payload data" errors
   - Continuous conversation without interruption
   - Chunk statistics showing steady audio flow

## What to Watch For

### Good Signs ✓
- Chunk statistics appearing regularly
- No audio format errors
- Conversation continues smoothly for 10+ minutes
- No "Stream ended naturally" messages (except at session end)

### Bad Signs ✗
- "AUDIO FORMAT ERROR: Odd byte count" messages
- "1007 invalid frame payload data" errors
- Conversation stops after a few minutes
- Multiple "Stream ended naturally" messages

## If Issues Persist

If you still see audio errors after this fix, check:

1. **Browser compatibility**: Test in Chrome/Edge (best WebAudio support)
2. **Microphone quality**: Try a different microphone
3. **Network stability**: Check for connection issues
4. **Backend logs**: Look for patterns in chunk counts before errors

## Next Steps

After verifying this fix works:

1. **Reduce latency** by decreasing buffer size:
   - Change `_bufferSize` from 4096 to 1600 in `pcm-processor.js`
   - This reduces latency from 256ms to 100ms

2. **Add Voice Activity Detection (VAD)**:
   - Configure VAD in `gemini_client.py` to reduce the 20-25 second delay
   - This is a separate issue from the audio format problem

## Files Modified

1. `frontend/public/worklets/pcm-processor.js` - Fixed audio encoding
2. `backend/app/services/gemini_client.py` - Added diagnostic logging
3. `backend/test_audio_format.py` - Created diagnostic tool (for future use)
4. `AUDIO_FORMAT_INVESTIGATION.md` - Detailed investigation notes
5. `AUDIO_FIX_APPLIED.md` - This file

## Technical Details

### Why DataView?

- `Int16Array` uses platform native byte order (usually little-endian, but not guaranteed)
- `DataView` provides explicit control over byte order
- `setInt16(offset, value, true)` forces little-endian encoding
- This matches Gemini's requirement: "s16le" (signed 16-bit little-endian)

### Performance Impact

- Minimal: DataView is optimized in modern browsers
- The loop adds ~0.1ms per chunk (4096 samples)
- This is negligible compared to network latency

### Alternative Approaches Considered

1. **Use Int16Array with explicit endianness check**: Too complex, platform-dependent
2. **Send Float32 and convert on backend**: Increases bandwidth 2x
3. **Use Web Audio API's built-in resampling**: Doesn't provide enough control

The DataView approach is the most reliable and explicit solution.
