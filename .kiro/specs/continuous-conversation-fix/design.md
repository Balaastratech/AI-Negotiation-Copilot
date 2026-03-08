# Continuous Conversation Fix Bugfix Design

## Overview

The Gemini Live API integration fails to maintain continuous bidirectional conversation because the `receive_responses` async loop exits when the Gemini Live stream naturally ends after each response. The root cause is that the Gemini Live API closes the response stream after each complete model turn, and the current implementation treats this as a terminal condition rather than a normal part of the conversation flow.

The fix requires implementing a keep-alive mechanism that restarts the receive loop when the stream ends naturally (not due to errors or cancellation), ensuring continuous listening throughout the entire negotiation session until explicit termination.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the Gemini Live response stream ends naturally after a model turn
- **Property (P)**: The desired behavior - the receive loop should continue listening for subsequent responses indefinitely
- **Preservation**: Existing session lifecycle, error handling, and message routing that must remain unchanged
- **receive_responses**: The async function in `gemini_client.py` that processes responses from the Gemini Live API
- **live_session**: The Gemini Live API session object that provides the bidirectional streaming interface
- **NegotiationState.ACTIVE**: The state during which the system should continuously process audio and provide responses
- **Session Handoff**: The mechanism that creates a new Gemini Live session after 540 seconds to work around API limitations
- **Interruption Handling**: The mechanism that detects when the user interrupts the AI mid-response

## Bug Details

### Fault Condition

The bug manifests when the Gemini Live API completes a model turn and closes the response stream. The `receive_responses` async loop exits because the `async for response in live_session.receive()` iterator completes normally, and there is no mechanism to restart the loop or maintain the listening state.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type StreamEndEvent
  OUTPUT: boolean
  
  RETURN input.stream_ended = true
         AND input.error = null
         AND input.cancellation = false
         AND session.state = NegotiationState.ACTIVE
         AND NOT user_initiated_end
END FUNCTION
```

### Examples

- User speaks: "I'd like to negotiate the price" → AI responds: "I can help with that" → Stream ends → User speaks again: "What's your best offer?" → System does not process or respond (BUG)

- User starts negotiation → AI provides opening guidance → Stream ends → User continues conversation → No AI response because receive loop has exited (BUG)

- User interrupts AI mid-response → Interruption flag is set → Stream ends → System should continue listening but receive loop exits (BUG)

- Session handoff triggers at 540 seconds → New session created → receive_responses task started → Stream ends after first response → Loop exits again (BUG persists across handoffs)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Explicit END_NEGOTIATION messages must continue to properly close the Gemini Live session and transition to ENDING state
- Audio encoding (16kHz PCM format) must remain unchanged
- Binary audio frame transmission through WebSocket must remain unchanged
- Transcription message handling (TRANSCRIPT_UPDATE) must remain unchanged
- Strategy update parsing and transmission must remain unchanged
- Vision frame processing must remain unchanged
- WebSocket connection loss handling must remain unchanged
- Privacy consent state transitions must remain unchanged
- Error handling and AI_DEGRADED messages must remain unchanged
- Session handoff mechanism timing and context summary must remain unchanged

**Scope:**
All inputs and behaviors that do NOT involve the natural stream end condition should be completely unaffected by this fix. This includes:
- All message types (PRIVACY_CONSENT_GRANTED, START_NEGOTIATION, VISION_FRAME, AUDIO_CHUNK, END_NEGOTIATION)
- Error conditions and exception handling
- State transitions and validation
- Audio/video data encoding and transmission

## Hypothesized Root Cause

Based on the code analysis, the root causes are:

1. **Stream Completion Treated as Terminal**: The `async for response in live_session.receive()` loop in `receive_responses` completes when the Gemini Live API closes the stream after a model turn. The code logs "stream may have closed" but does not attempt to continue listening.

2. **No Keep-Alive Mechanism**: There is no logic to detect that the stream ended naturally (vs. error/cancellation) and restart the receive loop to continue listening for subsequent user inputs.

3. **Single-Shot Task Creation**: In `negotiation_engine.py`, the `receive_responses` task is created once during `handle_start`, but when it exits, no new task is created to resume listening.

4. **Session Handoff Doesn't Fix Root Cause**: The session handoff mechanism creates a new Gemini Live session and starts a new `receive_responses` task, but that task also exits after the first response, so the bug persists.

## Correctness Properties

Property 1: Fault Condition - Continuous Listening After Stream End

_For any_ event where the Gemini Live response stream ends naturally (not due to error or cancellation) and the session state is ACTIVE, the fixed receive_responses function SHALL automatically restart the receive loop to continue listening for subsequent responses, maintaining continuous bidirectional conversation until explicit session termination.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation - Existing Session Lifecycle and Message Handling

_For any_ input or event that does NOT involve a natural stream end (including explicit END_NEGOTIATION, errors, cancellations, all message types, and state transitions), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing functionality for session management, message routing, audio/video processing, and error handling.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/app/services/gemini_client.py`

**Function**: `receive_responses`

**Specific Changes**:

1. **Add Keep-Alive Loop**: Wrap the existing `async for response in live_session.receive()` loop in an outer while loop that continues as long as the session should remain active.

2. **Add Session State Check**: Before restarting the receive loop, check if the session is still in ACTIVE state. If not, exit gracefully.

3. **Distinguish Normal End from Error**: When the stream ends, check if it was due to an error or cancellation (should exit) vs. normal completion (should continue).

4. **Add Logging**: Log when the stream ends naturally and the loop is restarting to aid debugging.

5. **Handle Interruptions Gracefully**: Ensure that when `sc.interrupted` is detected, the loop continues to listen for the next user input after sending the AUDIO_INTERRUPTED message.

**Pseudocode for Fixed Implementation**:
```python
async def receive_responses(live_session, websocket: WebSocket, session_id: str, session: NegotiationSession) -> None:
    try:
        # Outer keep-alive loop
        while session.state == NegotiationState.ACTIVE:
            try:
                # Inner loop processes responses from current stream
                async for response in live_session.receive():
                    # ... existing response processing logic ...
                    pass
                
                # Stream ended naturally - check if we should continue
                if session.state == NegotiationState.ACTIVE:
                    logger.info(f"Stream ended naturally, continuing to listen [{session_id}]")
                    # Loop will restart automatically
                else:
                    logger.info(f"Stream ended, session no longer active [{session_id}]")
                    break
                    
            except asyncio.CancelledError:
                logger.info(f"Receive loop cancelled [{session_id}]")
                raise
            except Exception as e:
                logger.error(f"Stream error [{session_id}]: {e}")
                # Error occurred - exit the keep-alive loop
                break
                
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Receive loop error [{session_id}]: {e}", exc_info=True)
```

**Alternative Approach (if stream doesn't naturally restart)**:

If the Gemini Live API requires explicit re-initialization of the receive stream, we may need to:
- Call a method like `live_session.start_listening()` or similar after each stream end
- Or implement a polling mechanism that checks for new responses
- Or use a different API pattern (e.g., separate send/receive channels)

This will be determined during exploratory testing.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by observing the receive loop exit after the first response, then verify the fix maintains continuous listening and preserves all existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the receive loop exits after the first AI response and does not process subsequent user input.

**Test Plan**: Create integration tests that simulate a multi-turn conversation by sending audio chunks, waiting for AI response, then sending more audio chunks. Add logging to track when the receive_responses task exits. Run these tests on the UNFIXED code to observe the premature exit.

**Test Cases**:
1. **Multi-Turn Conversation Test**: Start session → Send audio → Wait for AI response → Send more audio → Verify no response (will fail on unfixed code - second audio not processed)
2. **Interruption Test**: Start session → Send audio → While AI responding, send interruption audio → Verify interruption not handled (will fail on unfixed code)
3. **Session Handoff Test**: Start session → Wait 540+ seconds → Trigger handoff → Send audio → Wait for response → Send more audio → Verify no response (will fail on unfixed code - bug persists after handoff)
4. **Explicit End Test**: Start session → Send audio → Wait for response → Send END_NEGOTIATION → Verify clean shutdown (should pass on unfixed code - this is preservation)

**Expected Counterexamples**:
- After first AI response, the receive_responses task exits and logs "stream may have closed"
- Subsequent audio chunks are sent to Gemini but no responses are received
- The WebSocket remains open but no AI responses flow through
- Possible root cause confirmation: The `async for` loop completes when stream ends, and no restart mechanism exists

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (stream ends naturally during ACTIVE session), the fixed function continues listening and processing subsequent inputs.

**Pseudocode:**
```
FOR ALL stream_end_event WHERE isBugCondition(stream_end_event) DO
  result := receive_responses_fixed(live_session, websocket, session_id, session)
  ASSERT result.continues_listening = true
  ASSERT result.processes_next_input = true
  ASSERT result.provides_next_response = true
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (explicit end, errors, cancellations, all message types), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT receive_responses_original(input) = receive_responses_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain (different message types, state transitions, error conditions)
- It catches edge cases that manual unit tests might miss (e.g., race conditions, timing issues)
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for explicit END_NEGOTIATION, errors, and all message types, then write property-based tests capturing that exact behavior.

**Test Cases**:
1. **Explicit End Preservation**: Observe that END_NEGOTIATION cleanly closes session on unfixed code, verify same behavior after fix
2. **Error Handling Preservation**: Observe that stream errors cause receive loop to exit and send AI_DEGRADED on unfixed code, verify same behavior after fix
3. **Cancellation Preservation**: Observe that asyncio.CancelledError propagates correctly on unfixed code, verify same behavior after fix
4. **Message Routing Preservation**: Observe that all message types (PRIVACY_CONSENT_GRANTED, START_NEGOTIATION, VISION_FRAME, AUDIO_CHUNK) are processed correctly on unfixed code, verify same behavior after fix
5. **Audio Encoding Preservation**: Observe that audio chunks are encoded as 16kHz PCM on unfixed code, verify same behavior after fix
6. **Transcription Preservation**: Observe that TRANSCRIPT_UPDATE messages are sent correctly on unfixed code, verify same behavior after fix
7. **Strategy Update Preservation**: Observe that STRATEGY_UPDATE messages are parsed and sent correctly on unfixed code, verify same behavior after fix

### Unit Tests

- Test that receive_responses continues looping when stream ends naturally and session is ACTIVE
- Test that receive_responses exits when stream ends and session is not ACTIVE
- Test that receive_responses exits when asyncio.CancelledError is raised
- Test that receive_responses exits when an exception occurs in the stream
- Test that interruption handling sends AUDIO_INTERRUPTED and continues listening
- Test that session state check prevents restart when session has ended

### Property-Based Tests

- Generate random sequences of audio chunks and verify continuous processing across multiple AI responses
- Generate random session state transitions and verify receive loop behavior matches expected (continue or exit)
- Generate random error conditions and verify preservation of error handling behavior
- Generate random message sequences and verify all message types continue to work correctly

### Integration Tests

- Test full multi-turn conversation flow: user speaks → AI responds → user speaks → AI responds (repeat 5+ times)
- Test interruption flow: user speaks → AI starts responding → user interrupts → AI handles interruption → conversation continues
- Test session handoff flow: start session → have multi-turn conversation → wait for handoff → continue conversation seamlessly
- Test explicit end flow: start session → have conversation → send END_NEGOTIATION → verify clean shutdown
- Test error recovery flow: start session → simulate stream error → verify AI_DEGRADED message → verify session can be restarted
