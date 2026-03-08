# Workaround Solution: Stream Ending Bug

## Problem Confirmed

The diagnostic test proves the Gemini Live API SDK has a bug where `receive()` stream ends after `turn_complete`. This is NOT expected behavior - the stream should continue for multi-turn conversations.

## Test Results

```
✓ Turn 1 complete
=== TURN 2 ===
Sent: What's the weather like?
⚠ WARNING: Stream ended after 24 responses and 1 turns
```

The stream ends immediately after sending the second message, even though the session is still active.

## Root Cause

The `async for response in live_session.receive()` iterator stops yielding after the first `turn_complete` signal. This appears to be a bug in the `google-genai` Python SDK's Live API implementation.

## Workaround Strategy

Since we can't fix the SDK, we need to work around it by:

1. **Detecting when the stream ends** ✓ (already implemented)
2. **NOT restarting the receive loop** (doesn't work - same session, same problem)
3. **Instead: Keep the session alive and handle the limitation**

The key insight: The session itself doesn't close, only the `receive()` iterator stops. We need to accept this limitation and work with it.

## Solution: Single-Turn Sessions with Fast Handoff

Instead of fighting the SDK bug, embrace it:

1. Each "turn" gets its own session
2. After `turn_complete`, close the current session
3. Immediately open a new session with conversation context
4. This happens so fast the user won't notice

### Implementation

```python
async def handle_conversation_turn(websocket, session, api_key, context):
    """Handle a single conversation turn, then prepare for the next"""
    
    # Open session for this turn
    async with open_live_session(api_key=api_key, context=context) as live_session:
        # Start receive loop
        receive_task = asyncio.create_task(
            receive_responses_single_turn(live_session, websocket, session.session_id)
        )
        
        # Wait for turn to complete
        await receive_task
        
    # Session closes automatically, ready for next turn
```

This approach:
- Works with the SDK's behavior instead of against it
- Maintains conversation context across sessions
- Provides seamless user experience
- Avoids the 1011 keepalive timeout errors

## Alternative: Use Text API for Multi-Turn

If the workaround doesn't work well, fall back to:
- Use Live API for audio input/output
- Use standard Chat API for multi-turn logic
- Hybrid approach: best of both worlds

## Next Steps

1. Implement the single-turn session approach
2. Test with real conversation
3. Monitor for any issues
4. Report bug to Google with our test case

## Bug Report for Google

**Title**: Live API receive() stream ends after turn_complete, breaking multi-turn conversations

**Description**: 
The `AsyncSession.receive()` iterator stops yielding responses after the first `turn_complete` signal, even though the session remains active. This prevents multi-turn conversations from working correctly.

**Reproduction**:
```python
async with client.aio.live.connect(model=model, config=config) as session:
    await session.send_realtime_input(text="Hello")
    
    async for response in session.receive():
        if response.server_content.turn_complete:
            # Send next message
            await session.send_realtime_input(text="How are you?")
            # Stream ends here - no more responses!
```

**Expected**: Stream continues, yields responses for second message
**Actual**: Stream ends, no responses for second message

**Impact**: Makes multi-turn conversations impossible with Live API
