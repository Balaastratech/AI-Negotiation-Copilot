"""
Bug Condition Exploration Test for Continuous Conversation Fix

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

This test explores the bug condition where the receive_responses loop exits
after the first AI response when the Gemini Live stream ends naturally.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Expected behavior on UNFIXED code:
- Test will FAIL because receive_responses exits after first response
- Second audio chunk will not be processed
- No second AI response will be received
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncIterator

from app.services.gemini_client import GeminiClient
from app.models.negotiation import NegotiationSession, NegotiationState

logger = logging.getLogger(__name__)


class MockServerContent:
    """Mock for Gemini server content response"""
    def __init__(self, has_audio=False, has_text=False, interrupted=False):
        self.interrupted = interrupted
        self.model_turn = None
        self.input_transcription = None
        self.output_transcription = None
        
        if has_audio or has_text:
            self.model_turn = MagicMock()
            self.model_turn.parts = []
            
            if has_audio:
                audio_part = MagicMock()
                audio_part.inline_data = MagicMock()
                audio_part.inline_data.mime_type = "audio/pcm"
                audio_part.inline_data.data = b"fake_audio_data"
                audio_part.text = None
                self.model_turn.parts.append(audio_part)
            
            if has_text:
                text_part = MagicMock()
                text_part.inline_data = None
                text_part.text = "AI response text"
                self.model_turn.parts.append(text_part)


class MockResponse:
    """Mock for Gemini response"""
    def __init__(self, server_content):
        self.server_content = server_content


class MockLiveSession:
    """
    Mock Gemini Live session that simulates the bug:
    - First call to receive() yields one response then ends the stream
    - Subsequent calls to receive() should yield more responses but won't be called due to bug
    """
    def __init__(self):
        self.receive_call_count = 0
        self.responses_sent = 0
        
    async def receive(self) -> AsyncIterator[MockResponse]:
        """
        Simulate Gemini Live API behavior:
        - Stream ends after each model turn (this is normal Gemini behavior)
        - On unfixed code, receive_responses won't call this again
        """
        self.receive_call_count += 1
        logger.info(f"MockLiveSession.receive() called (call #{self.receive_call_count})")
        
        # First call: yield one AI response then end stream
        if self.receive_call_count == 1:
            logger.info("Yielding first AI response")
            self.responses_sent += 1
            yield MockResponse(MockServerContent(has_audio=True, has_text=True))
            logger.info("First stream ended naturally (simulating Gemini behavior)")
            return
        
        # Second call: would yield second response if receive_responses continues
        if self.receive_call_count == 2:
            logger.info("Yielding second AI response")
            self.responses_sent += 1
            yield MockResponse(MockServerContent(has_audio=True, has_text=True))
            logger.info("Second stream ended naturally")
            return
        
        # Subsequent calls - limit to prevent infinite loop in tests
        if self.receive_call_count <= 5:  # Allow up to 5 calls total
            logger.info(f"Yielding response #{self.responses_sent + 1}")
            self.responses_sent += 1
            yield MockResponse(MockServerContent(has_audio=True, has_text=True))
            return
        
        # After 5 calls, wait indefinitely to simulate blocking behavior
        logger.info(f"MockLiveSession.receive() call #{self.receive_call_count} - waiting indefinitely (simulating no more data)")
        await asyncio.Event().wait()  # Block forever to simulate waiting for data that never comes
        return


@pytest.mark.asyncio
async def test_bug_condition_continuous_listening_after_stream_end():
    """
    Property 1: Fault Condition - Continuous Listening After Stream End
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
    
    CRITICAL: This test MUST FAIL on unfixed code.
    
    Test Strategy:
    1. Start a session in ACTIVE state
    2. Send first audio chunk
    3. Wait for first AI response
    4. Stream ends naturally (normal Gemini behavior)
    5. Send second audio chunk
    6. Verify system processes second audio and provides response
    
    Expected on UNFIXED code:
    - receive_responses exits after first response
    - MockLiveSession.receive() is only called once
    - Second audio is sent but no second response received
    - Test FAILS with assertion error
    
    Expected on FIXED code:
    - receive_responses continues listening after stream end
    - MockLiveSession.receive() is called twice
    - Second audio is processed and second response received
    - Test PASSES
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-session-123"
    mock_live_session = MockLiveSession()
    
    # Create a session in ACTIVE state
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Track messages sent through websocket
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
        logger.info(f"WebSocket sent JSON: {msg.get('type')}")
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
        logger.info(f"WebSocket sent audio frame: {len(data)} bytes")
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting receive_responses task")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for first response to be processed
    logger.info("Waiting for first AI response...")
    await asyncio.sleep(0.5)
    
    # Verify first response was received
    assert len(audio_frames_sent) >= 1, "Should have received first audio response"
    logger.info(f"First response received: {len(audio_frames_sent)} audio frames")
    
    # At this point, the stream has ended naturally
    # On UNFIXED code: receive_responses task exits here
    # On FIXED code: receive_responses continues listening
    
    # Simulate sending second audio chunk (user continues speaking)
    logger.info("Simulating second audio input (user continues speaking)...")
    await asyncio.sleep(0.5)
    
    # Check if receive_responses is still running
    if receive_task.done():
        logger.error("BUG DETECTED: receive_responses task exited after first response!")
        logger.error("This confirms the bug - the loop exits when stream ends naturally")
    else:
        logger.info("receive_responses task still running (expected on fixed code)")
    
    # Wait a bit more to see if second response would be processed
    await asyncio.sleep(0.5)
    
    # Cancel the task for cleanup
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # CRITICAL ASSERTIONS - These will FAIL on unfixed code
    
    # Bug Condition Check 1: receive() should be called multiple times
    assert mock_live_session.receive_call_count >= 2, (
        f"BUG CONFIRMED: receive() only called {mock_live_session.receive_call_count} time(s). "
        f"Expected at least 2 calls for continuous conversation. "
        f"The receive_responses loop exits after first stream end instead of continuing."
    )
    
    # Bug Condition Check 2: Multiple responses should be processed
    assert mock_live_session.responses_sent >= 2, (
        f"BUG CONFIRMED: Only {mock_live_session.responses_sent} response(s) sent. "
        f"Expected at least 2 responses for multi-turn conversation. "
        f"System stops listening after first AI response."
    )
    
    # Bug Condition Check 3: Multiple audio frames should be received
    assert len(audio_frames_sent) >= 2, (
        f"BUG CONFIRMED: Only {len(audio_frames_sent)} audio frame(s) received. "
        f"Expected at least 2 frames for continuous conversation. "
        f"Second audio input not processed because receive loop exited."
    )
    
    logger.info("✓ Test PASSED: Continuous listening maintained after stream end")
    logger.info(f"  - receive() called {mock_live_session.receive_call_count} times")
    logger.info(f"  - {mock_live_session.responses_sent} responses processed")
    logger.info(f"  - {len(audio_frames_sent)} audio frames received")


@pytest.mark.asyncio
async def test_bug_condition_with_session_state_check():
    """
    Additional test: Verify the bug occurs even with session state checks
    
    This test confirms that the bug is not due to session state changes,
    but specifically due to the receive loop exiting when stream ends.
    """
    mock_websocket = AsyncMock()
    session_id = "test-session-456"
    mock_live_session = MockLiveSession()
    
    # Create session that stays ACTIVE throughout
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    audio_frames_sent = []
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = AsyncMock()
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for processing
    await asyncio.sleep(1.0)
    
    # Verify session is still ACTIVE
    assert session.state == NegotiationState.ACTIVE, "Session should remain ACTIVE"
    
    # Check if task exited despite ACTIVE state
    task_exited = receive_task.done()
    
    # Cleanup
    if not task_exited:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
    
    # On unfixed code: task exits even though session is ACTIVE
    # This proves the bug is in the receive loop logic, not session state
    if task_exited:
        logger.error("BUG CONFIRMED: receive_responses exited despite session being ACTIVE")
        logger.error("This proves the bug is in the receive loop, not session state management")
    
    # This assertion will FAIL on unfixed code
    assert not task_exited, (
        "BUG CONFIRMED: receive_responses task exited even though session is ACTIVE. "
        "The bug is in the receive loop logic - it exits when stream ends naturally "
        "instead of continuing to listen for subsequent user input."
    )
    
    logger.info("✓ Test PASSED: receive_responses continues while session is ACTIVE")
