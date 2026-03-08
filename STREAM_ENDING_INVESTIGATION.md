# Stream Ending Investigation

## Problem

The Gemini Live API `receive()` stream is ending after the first turn completes (30 responses), causing:
1. The receive loop to exit
2. Subsequent audio chunks to fail with "1011 keepalive ping timeout"
3. No more responses from the AI

## Evidence from Logs

```
INFO: Turn complete signal received (response #30)
WARNING: Gemini receive loop ended after 30 responses - THIS SHOULD NOT HAPPEN
ERROR: Audio chunk send failed: sent 1011 keepalive ping timeout; no close frame received
```

## Timeline

1. Session starts successfully
2. User speaks → AI responds (30 response chunks)
3. `turn_complete` signal received
4. **Stream ends** (this is the bug)
5. Frontend continues sending audio
6. Backend tries to send audio to dead connection → 1011 errors
7. User sees: AI responds once, then stops listening

## Root Cause Hypothesis

The `async for response in live_session.receive()` loop is exiting naturally, which means:

1. **Possibility 1**: The Gemini SDK's `receive()` generator is stopping after `turn_complete`
   - This would be a SDK bug or misuse
   - The stream should continue until session is explicitly closed

2. **Possibility 2**: Something in our code is closing the session
   - Checked: No code closes the session during active conversation
   - Only closed on END_NEGOTIATION or unregister

3. **Possibility 3**: The SDK requires explicit "continue listening" signal
   - Maybe we need to send something after `turn_complete`?
   - Or configure the session differently?

## What We Know About Gemini Live API

From the SDK and documentation:
- `receive()` should yield responses continuously
- `turn_complete` signals end of ONE turn, not the conversation
- The stream should stay open for multi-turn conversations
- WebSocket should maintain keepalive automatically

## Potential Fixes

### Fix 1: Check SDK Version and Update

The SDK might have a bug in older versions. Check:
```bash
pip show google-genai
```

Update to latest:
```bash
pip install --upgrade google-genai
```

### Fix 2: Add Explicit Turn Acknowledgment

Maybe the SDK expects us to acknowledge turn completion:

```python
if hasattr(sc, 'turn_complete') and sc.turn_complete:
    logger.info(f"Turn complete, continuing to listen [{session_id}]")
    # Try sending empty audio or explicit continue signal?
    # await live_session.send_realtime_input(...)
```

### Fix 3: Restart receive() Loop on Exit

If the stream ends, restart it:

```python
async def receive_responses(live_session, websocket: WebSocket, session_id: str) -> None:
    while True:  # Keep trying to receive
        try:
            logger.info(f"Starting receive loop [{session_id}]")
            response_count = 0
            
            async for response in live_session.receive():
                # ... process responses ...
                
            # If we get here, stream ended unexpectedly
            logger.warning(f"Stream ended after {response_count} responses, restarting...")
            await asyncio.sleep(0.1)  # Brief pause before restart
            
        except asyncio.CancelledError:
            logger.info(f"Receive loop cancelled [{session_id}]")
            break
        except Exception as e:
            logger.error(f"Receive loop error [{session_id}]: {e}")
            break
```

### Fix 4: Use Different API Configuration

Maybe we need to configure the session differently:

```python
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    # Add these?
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            preemptible=True  # Allow interruptions
        )
    ),
    # Or configure turn detection differently?
)
```

### Fix 5: Check for SDK Context Manager Issue

The `async with client.aio.live.connect()` might be closing prematurely. Try:

```python
# Instead of storing the context manager
session.live_session_cm = live_session_cm
session.live_session = await live_session_cm.__aenter__()

# Try storing the session directly without context manager
session.live_session = await client.aio.live.connect(model=model, config=config)
```

## Next Steps

1. **Run the test script** `backend/test_continuous_receive.py` to see if the issue reproduces
2. **Check SDK version** and update if needed
3. **Try Fix 3** (restart loop) as a quick workaround
4. **Research SDK documentation** for multi-turn conversation examples
5. **Check SDK GitHub issues** for similar problems

## Test Script

Run this to isolate the issue:

```bash
cd backend
python test_continuous_receive.py
```

This will:
- Connect to Gemini Live API
- Send 3 messages in sequence
- Check if the stream continues after each turn
- Report whether the stream ends prematurely

Expected output:
```
✓ Connected!
=== TURN 1 ===
Sent: Hello, how are you?
Response #1-30: [AI response]
✓ Turn 1 complete
=== TURN 2 ===
Sent: What's the weather like?
Response #31-60: [AI response]
✓ Turn 2 complete
=== TURN 3 ===
...
```

If the stream ends after Turn 1, we've confirmed the bug.

## Workaround for Users

Until fixed, users can:
1. Refresh the page after each AI response
2. Click "End Session" and "Start New Session" between questions
3. Wait for the fix

This is obviously not acceptable for production.
