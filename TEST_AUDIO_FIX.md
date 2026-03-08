# Testing the Audio Format Fix

## Quick Test (5 minutes)

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

3. **Open the app** in Chrome/Edge (best WebAudio support)

4. **Have a conversation**:
   - Grant microphone permissions
   - Start a negotiation session
   - Talk for at least 5 minutes
   - Try multiple back-and-forth exchanges

5. **Watch the terminal** for:
   ```
   Audio stats: chunk #100, 8192 bytes, 4096 samples, 256.0ms @ 16kHz
   Audio stats: chunk #200, 8192 bytes, 4096 samples, 256.0ms @ 16kHz
   Audio stats: chunk #300, 8192 bytes, 4096 samples, 256.0ms @ 16kHz
   ```

## Success Criteria

✓ **No "1007 invalid frame payload data" errors**
✓ **Conversation continues smoothly for 5+ minutes**
✓ **Chunk statistics appear regularly**
✓ **No "AUDIO FORMAT ERROR" messages**

## If You See Errors

### Error: "Odd byte count"
```
AUDIO FORMAT ERROR: Odd byte count 8193 - incomplete Int16 sample!
```
**Cause**: Buffer accumulation issue in worklet
**Fix**: Check the `_resampleAccumulator` logic in `pcm-processor.js`

### Error: "1007 invalid frame payload data"
```
ERROR: 1007 invalid frame payload data - error when processing input audio
```
**Cause**: Audio format still incorrect
**Fix**: Verify the DataView encoding is being used (check browser console for errors)

### Error: "Stream ended naturally"
```
INFO: Stream ended naturally, continuing to listen
```
**Cause**: This is a different issue (not audio format related)
**Fix**: This was the previous bug - should not happen with the current code

## Long Test (10+ minutes)

After the quick test passes:

1. **Run for 10+ minutes** to verify long-term stability
2. **Try interrupting** the AI while it's speaking
3. **Try rapid back-and-forth** exchanges
4. **Monitor memory usage** in browser DevTools

## Expected Chunk Statistics

At 16kHz with 4096 samples per chunk:
- **Chunk duration**: 256ms (4096 / 16000)
- **Chunks per second**: ~3.9
- **Chunks per minute**: ~234
- **Chunks in 5 minutes**: ~1170

So after 5 minutes, you should see:
```
Audio stats: chunk #1100, 8192 bytes, 4096 samples, 256.0ms @ 16kHz
```

## Debugging Tips

### Check Browser Console

Open DevTools (F12) and look for:
- AudioWorklet errors
- WebSocket errors
- Memory leaks

### Check Network Tab

- WebSocket connection should stay open
- Binary frames should be ~8KB each
- No reconnection attempts

### Check Backend Logs

- Look for patterns in chunk counts
- Check for any warnings before errors
- Monitor memory usage with `htop` or Task Manager

## Next Steps After Success

Once this fix is verified:

1. **Reduce buffer size** for lower latency:
   - Change `_bufferSize` from 4096 to 1600
   - Test again to verify no issues

2. **Add VAD configuration** to fix the 20-25 second delay:
   - This is a separate issue
   - Will be addressed after audio format is stable

3. **Run the full test suite**:
   ```bash
   cd backend
   pytest tests/test_continuous_conversation_bug.py -v
   pytest tests/test_preservation_properties.py -v
   ```

## Rollback Plan

If the fix causes new issues:

1. **Revert frontend changes**:
   ```bash
   git checkout frontend/public/worklets/pcm-processor.js
   ```

2. **Keep backend logging**:
   - The diagnostic logging is helpful for debugging
   - No need to revert `gemini_client.py`

3. **Report the issue**:
   - Include browser version
   - Include error messages
   - Include chunk statistics before error
