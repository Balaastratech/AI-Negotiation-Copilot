# Audio Format Investigation

## Problem Summary

After a few minutes of conversation, the Gemini Live API rejects audio with error:
```
ERROR: 1007 invalid frame payload data - error when processing input audio, 
please check if the inputaudio is in valid format: 16khz s16le pcm, mono channel
```

## Key Observations

1. **Timing**: Error occurs after "a few minutes" - not immediately
2. **Pattern**: Multiple "Stream ended naturally" messages before the error
3. **Format**: Gemini expects "s16le" = signed 16-bit little-endian PCM
4. **Symptom**: Audio works initially, then becomes corrupted over time

## Root Cause Hypothesis

The audio corruption likely occurs in the **frontend audio processing pipeline**, specifically in `pcm-processor.js`.

### Current Audio Pipeline

```
Microphone (Float32, 48kHz)
  ↓
AudioWorklet: pcm-processor.js
  ↓ Decimation (48kHz → 16kHz)
  ↓ Conversion (Float32 → Int16)
  ↓
Int16Array buffer
  ↓
ArrayBuffer via postMessage
  ↓
WebSocket.send(ArrayBuffer)
  ↓
Backend receives bytes
  ↓
Gemini Live API
```

### Potential Issues

1. **Buffer Accumulation**: The worklet accumulates samples in `this._buffer` array
   - JavaScript arrays don't guarantee memory layout
   - Converting to Int16Array might have endianness issues
   
2. **Resample Accumulator**: The `_resampleAccumulator` might drift over time
   - Could cause sample misalignment
   - Could result in odd byte counts (incomplete samples)

3. **Int16 Conversion**: The conversion `s < 0 ? s * 0x8000 : s * 0x7fff`
   - Pushes raw numbers to array
   - Int16Array constructor might not handle this correctly on all platforms

## Diagnostic Logging Added

### Backend Changes

Added to `gemini_client.py`:

1. **Audio chunk validation**:
   - Check for odd byte counts (incomplete Int16 samples)
   - Check for empty chunks
   - Log statistics every 100 chunks

2. **Enhanced error logging**:
   - Detect audio format errors specifically
   - Log total chunks sent before error
   - Provide detailed error context

### What to Look For

When you run the app, watch for:

1. **Chunk statistics** (every 100 chunks):
   ```
   Audio stats: chunk #100, 8192 bytes, 4096 samples, 256.0ms @ 16kHz
   ```

2. **Format errors**:
   ```
   AUDIO FORMAT ERROR: Odd byte count 8193 - incomplete Int16 sample!
   ```

3. **Error timing**:
   - How many chunks were sent before the 1007 error?
   - Does it always happen at the same chunk count?

## Recommended Fixes

### Fix 1: Ensure Proper Int16 Encoding (RECOMMENDED)

Modify `pcm-processor.js` to use DataView for guaranteed little-endian encoding:

```javascript
if (this._buffer.length >= this._bufferSize) {
  const samples = this._buffer.splice(0, this._bufferSize);
  const arrayBuffer = new ArrayBuffer(samples.length * 2);
  const dataView = new DataView(arrayBuffer);
  
  for (let i = 0; i < samples.length; i++) {
    // Explicitly write as little-endian Int16
    dataView.setInt16(i * 2, samples[i], true); // true = little-endian
  }
  
  this.port.postMessage(arrayBuffer, [arrayBuffer]);
}
```

### Fix 2: Reduce Buffer Size

Change `_bufferSize` from 4096 to 1600 samples (100ms instead of 256ms):
- Reduces latency
- Reduces chance of buffer corruption
- Aligns better with typical VAD frame sizes

### Fix 3: Add Buffer Validation

Add validation before sending:

```javascript
if (this._buffer.length >= this._bufferSize) {
  const samples = this._buffer.splice(0, this._bufferSize);
  
  // Validate samples
  const hasInvalid = samples.some(s => !Number.isFinite(s) || s < -32768 || s > 32767);
  if (hasInvalid) {
    console.error('Invalid samples detected, skipping chunk');
    return true;
  }
  
  // ... rest of encoding
}
```

## Testing Plan

1. **Run with current logging**:
   - Start the app
   - Have a conversation for 5+ minutes
   - Watch the terminal for chunk statistics and errors
   - Note the chunk count when error occurs

2. **Apply Fix 1** (DataView encoding):
   - Modify `pcm-processor.js`
   - Test again for 5+ minutes
   - Verify no 1007 errors

3. **Apply Fix 2** (reduce buffer size):
   - Change `_bufferSize` to 1600
   - Test latency improvement
   - Verify audio quality

4. **Monitor long-term stability**:
   - Run for 10+ minutes
   - Verify no degradation over time

## Next Steps

1. Run the app with the new diagnostic logging
2. Observe the chunk statistics and error patterns
3. Apply Fix 1 (DataView encoding) to `frontend/public/worklets/pcm-processor.js`
4. Test and verify the fix resolves the issue
5. If issue persists, investigate other potential causes:
   - WebSocket frame fragmentation
   - Backend buffer handling
   - Gemini API session state

## Files Modified

- `backend/app/services/gemini_client.py` - Added diagnostic logging
- `backend/test_audio_format.py` - Created diagnostic tool

## Files to Modify Next

- `frontend/public/worklets/pcm-processor.js` - Apply Fix 1 (DataView encoding)
