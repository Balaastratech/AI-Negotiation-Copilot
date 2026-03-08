# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Continuous Listening After Stream End
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the receive loop exits after first AI response
  - **Scoped PBT Approach**: Scope the property to concrete failing case: multi-turn conversation where stream ends naturally after first response
  - Test that receive_responses continues listening after stream ends naturally during ACTIVE session
  - Simulate: Start session → Send audio → Wait for AI response → Stream ends → Send more audio → Verify system processes second audio
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (receive loop exits after first response, second audio not processed)
  - Document counterexamples found: "After first AI response, receive_responses task exits and logs 'stream may have closed'. Subsequent audio chunks sent but no responses received."
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Session Lifecycle and Message Handling
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (explicit END_NEGOTIATION, errors, cancellations, all message types)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - Explicit END_NEGOTIATION cleanly closes session and transitions to ENDING state
    - Stream errors cause receive loop to exit and send AI_DEGRADED message
    - asyncio.CancelledError propagates correctly
    - All message types (PRIVACY_CONSENT_GRANTED, START_NEGOTIATION, VISION_FRAME, AUDIO_CHUNK) are processed correctly
    - Audio encoding (16kHz PCM format) remains unchanged
    - Transcription messages (TRANSCRIPT_UPDATE) are sent correctly
    - Strategy update parsing and transmission works correctly
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 3. Fix for continuous conversation stream handling

  - [x] 3.1 Implement keep-alive loop in receive_responses function
    - Wrap existing `async for response in live_session.receive()` loop in outer while loop
    - Add condition: `while session.state == NegotiationState.ACTIVE`
    - Add session state check after stream ends to determine if loop should continue
    - Distinguish normal stream end from error/cancellation conditions
    - Add logging for stream restart events: "Stream ended naturally, continuing to listen"
    - Ensure interruption handling continues listening after sending AUDIO_INTERRUPTED message
    - _Bug_Condition: isBugCondition(input) where input.stream_ended = true AND input.error = null AND input.cancellation = false AND session.state = NegotiationState.ACTIVE_
    - _Expected_Behavior: receive_responses SHALL automatically restart the receive loop to continue listening for subsequent responses, maintaining continuous bidirectional conversation_
    - _Preservation: Explicit END_NEGOTIATION, error handling, cancellation, all message types, audio encoding, transcription, strategy updates must remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 3.2 Update receive_responses signature to accept session parameter
    - Add `session: NegotiationSession` parameter to receive_responses function signature
    - This enables the keep-alive loop to check session.state
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Update all call sites to pass session parameter
    - Update call in negotiation_engine.py handle_start method
    - Update call in negotiation_engine.py handle_session_handoff method
    - Pass the session object to receive_responses task
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Continuous Listening After Stream End
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms receive loop continues after stream end, processes subsequent audio)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Session Lifecycle and Message Handling
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in explicit end, error handling, message routing, audio encoding, transcription, strategy updates)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 4. Write integration tests for multi-turn conversation
  - Test full conversation flow: user speaks → AI responds → user speaks → AI responds (repeat 5+ times)
  - Verify continuous bidirectional communication throughout entire session
  - Verify no receive loop exits between responses
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5. Write integration tests for interruption handling
  - Test interruption flow: user speaks → AI starts responding → user interrupts → AI handles interruption → conversation continues
  - Verify AUDIO_INTERRUPTED message is sent
  - Verify receive loop continues listening after interruption
  - Verify subsequent user input is processed correctly
  - _Requirements: 2.5, 2.6_

- [x] 6. Write integration tests for session handoff
  - Test session handoff flow: start session → have multi-turn conversation → wait for handoff → continue conversation seamlessly
  - Verify new session is created at 540 seconds
  - Verify receive_responses task is restarted with new session
  - Verify conversation continues without interruption
  - Verify keep-alive loop works correctly in new session
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
