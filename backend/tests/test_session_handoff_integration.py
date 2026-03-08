"""
Integration Tests for Session Handoff

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

These tests verify that the session handoff mechanism works correctly with the
keep-alive loop, ensuring continuous conversation across session boundaries.

Test Strategy:
- Test session handoff flow: start session → have multi-turn conversation → 
  wait for handoff → continue conversation seamlessly
- Verify new session is created at 540 seconds
- Verify receive_responses task is restarted with new session
- Verify conversation continues without interruption
- Verify keep-alive loop works correctly in new session
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from app.services.gemini_client import GeminiClient, SESSION_HANDOFF_TRIGGER
from app.services.negotiation_engine import NegotiationEngine
from app.models.negotiation import NegotiationSession, NegotiationState

logger = logging.getLogger(__name__)


# ============================================================================
# Mock Classes for Testing
# ============================================================================

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


class MockLiveSessionForHandoff:
    """
    Mock Gemini Live session that simulates continuous conversation
    across session handoff boundaries.
    """
    def __init__(self, session_id: str, is_new_session: bool = False, max_responses: int = 5):
        self.session_id = session_id
        self.is_new_session = is_new_session
        self.receive_call_count = 0
        self.responses_sent = 0
        self.closed = False
        self.max_responses = max_responses
        
    async def receive(self) -> AsyncIterator[MockResponse]:
        """
        Simulate Gemini Live API behavior:
        - Stream ends after each model turn (normal Gemini behavior)
        - Keep-alive loop should call this multiple times
        - Limit responses to prevent infinite loops in tests
        """
        self.receive_call_count += 1
        logger.info(
            f"MockLiveSession.receive() called (call #{self.receive_call_count}, "
            f"new_session={self.is_new_session}, session_id={self.session_id})"
        )
        
        # Limit responses to prevent infinite loops
        if self.responses_sent >= self.max_responses:
            logger.info(f"Max responses ({self.max_responses}) reached, blocking indefinitely")
            # Block indefinitely to simulate waiting for more data
            await asyncio.Event().wait()
            return
        
        # Yield one response then end stream
        self.responses_sent += 1
        yield MockResponse(MockServerContent(has_audio=True, has_text=True))
        logger.info(f"Stream ended naturally (call #{self.receive_call_count})")
        return
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Mock context manager exit"""
        self.closed = True
        logger.info(f"MockLiveSession closed (session_id={self.session_id})")


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_session_handoff_creates_new_session():
    """
    Test that session handoff creates a new Gemini Live session at 540 seconds
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start a session with monitor_session_lifetime
    2. Mock time to trigger handoff at 540 seconds
    3. Verify old session is closed
    4. Verify new session is created
    5. Verify receive_responses is restarted with new session
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-handoff-123"
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    session.context = "Test negotiation context"
    
    # Track session creation
    sessions_created = []
    old_session = MockLiveSessionForHandoff(session_id, is_new_session=False)
    new_session = MockLiveSessionForHandoff(session_id, is_new_session=True)
    
    async def mock_open_live_session(api_key: str, context: str):
        """Mock session creation"""
        logger.info(f"Creating new live session with context: {context[:100]}...")
        sessions_created.append({"context": context})
        return new_session
    
    # Set initial session
    session.live_session = old_session
    
    # Mock asyncio.sleep to speed up test
    original_sleep = asyncio.sleep
    
    async def fast_sleep(duration):
        if duration == SESSION_HANDOFF_TRIGGER:
            # Fast-forward to handoff trigger
            logger.info(f"Fast-forwarding {duration} seconds to trigger handoff")
            await original_sleep(0.1)
        else:
            await original_sleep(duration)
    
    # Track receive_responses tasks
    receive_tasks_created = []
    original_create_task = asyncio.create_task
    
    def track_create_task(coro):
        task = original_create_task(coro)
        # Check if this is a receive_responses task
        if hasattr(coro, '__name__') and 'receive_responses' in str(coro):
            receive_tasks_created.append(task)
            logger.info(f"receive_responses task created (total: {len(receive_tasks_created)})")
        return task
    
    # Execute with mocks
    with patch('asyncio.sleep', fast_sleep), \
         patch('asyncio.create_task', track_create_task), \
         patch.object(GeminiClient, 'open_live_session', mock_open_live_session):
        
        # Start monitor_session_lifetime
        monitor_task = asyncio.create_task(
            GeminiClient.monitor_session_lifetime(session, mock_websocket, "test-api-key")
        )
        
        # Wait for handoff to complete
        await asyncio.sleep(0.5)
        
        # Cancel monitor task (it would recursively call itself)
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    # Verify handoff occurred
    assert len(sessions_created) >= 1, "Should create at least one new session"
    assert "CONTINUATION CONTEXT" in sessions_created[0]["context"], \
        "New session should include continuation context"
    
    # Verify old session was closed
    assert old_session.closed, "Old session should be closed"
    
    # Verify new session was set
    assert session.live_session == new_session, "Session should reference new live session"
    
    # Verify receive_responses was restarted
    assert len(receive_tasks_created) >= 1, "Should create receive_responses task for new session"
    
    logger.info("✓ Session handoff creates new session correctly")
    logger.info(f"  - Sessions created: {len(sessions_created)}")
    logger.info(f"  - receive_responses tasks: {len(receive_tasks_created)}")


@pytest.mark.asyncio
async def test_session_handoff_continues_conversation():
    """
    Test that conversation continues seamlessly across session handoff
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start session and have multi-turn conversation
    2. Trigger session handoff
    3. Continue conversation with new session
    4. Verify no interruption in conversation flow
    5. Verify keep-alive loop works in both old and new sessions
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-handoff-conversation"
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Track messages and audio
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
    
    # Create old and new sessions
    old_session = MockLiveSessionForHandoff(session_id, is_new_session=False)
    new_session = MockLiveSessionForHandoff(session_id, is_new_session=True)
    
    # Start with old session
    session.live_session = old_session
    
    # Start receive_responses with old session
    logger.info("Starting receive_responses with old session")
    old_receive_task = asyncio.create_task(
        GeminiClient.receive_responses(old_session, mock_websocket, session_id, session)
    )
    
    # Wait for first response from old session
    await asyncio.sleep(0.3)
    initial_audio_count = len(audio_frames_sent)
    assert initial_audio_count >= 1, "Should receive responses from old session"
    logger.info(f"Received {initial_audio_count} audio frames from old session")
    
    # Simulate session handoff - replace session
    logger.info("Simulating session handoff...")
    old_session.closed = True
    session.live_session = new_session
    
    # Start receive_responses with new session
    logger.info("Starting receive_responses with new session")
    new_receive_task = asyncio.create_task(
        GeminiClient.receive_responses(new_session, mock_websocket, session_id, session)
    )
    
    # Wait for responses from new session
    await asyncio.sleep(0.3)
    final_audio_count = len(audio_frames_sent)
    
    # Verify conversation continued with new session
    assert final_audio_count > initial_audio_count, \
        "Should receive additional responses from new session"
    logger.info(
        f"Received {final_audio_count - initial_audio_count} additional audio frames "
        f"from new session"
    )
    
    # Verify both sessions processed multiple receive() calls (keep-alive working)
    assert old_session.receive_call_count >= 2, \
        f"Old session should have multiple receive() calls (got {old_session.receive_call_count})"
    assert new_session.receive_call_count >= 2, \
        f"New session should have multiple receive() calls (got {new_session.receive_call_count})"
    
    # Cleanup
    session.state = NegotiationState.ENDING
    await asyncio.sleep(0.1)
    
    for task in [old_receive_task, new_receive_task]:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    logger.info("✓ Conversation continues seamlessly across session handoff")
    logger.info(f"  - Old session: {old_session.receive_call_count} receive() calls, "
                f"{old_session.responses_sent} responses")
    logger.info(f"  - New session: {new_session.receive_call_count} receive() calls, "
                f"{new_session.responses_sent} responses")
    logger.info(f"  - Total audio frames: {final_audio_count}")


@pytest.mark.asyncio
async def test_session_handoff_preserves_context():
    """
    Test that session handoff preserves conversation context
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start session with initial context
    2. Add strategy updates and transcripts
    3. Trigger session handoff
    4. Verify new session receives continuation context with:
       - Original context
       - Last strategy
       - Recent transcript
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-handoff-context"
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    session.context = "Negotiating price for a car"
    
    # Add conversation history
    session.strategy_history = [
        {"approach": "collaborative", "priority": "price"},
        {"approach": "competitive", "priority": "warranty"}
    ]
    session.transcript = [
        {"speaker": "user", "text": "I want to buy this car"},
        {"speaker": "ai", "text": "Let's discuss the price"},
        {"speaker": "user", "text": "What's your best offer?"}
    ]
    
    # Track session creation
    contexts_used = []
    
    async def mock_open_live_session(api_key: str, context: str):
        """Mock session creation and capture context"""
        logger.info(f"Creating session with context:\n{context}")
        contexts_used.append(context)
        return MockLiveSessionForHandoff(session_id, is_new_session=True)
    
    # Set initial session
    old_session = MockLiveSessionForHandoff(session_id, is_new_session=False)
    session.live_session = old_session
    
    # Mock asyncio.sleep to speed up test
    original_sleep = asyncio.sleep
    
    async def fast_sleep(duration):
        if duration == SESSION_HANDOFF_TRIGGER:
            await original_sleep(0.1)
        else:
            await original_sleep(duration)
    
    # Execute with mocks
    with patch('asyncio.sleep', fast_sleep), \
         patch.object(GeminiClient, 'open_live_session', mock_open_live_session):
        
        # Start monitor_session_lifetime
        monitor_task = asyncio.create_task(
            GeminiClient.monitor_session_lifetime(session, mock_websocket, "test-api-key")
        )
        
        # Wait for handoff
        await asyncio.sleep(0.5)
        
        # Cancel monitor task
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    # Verify context was preserved
    assert len(contexts_used) >= 1, "Should create at least one new session"
    new_context = contexts_used[0]
    
    # Verify original context is included
    assert "Negotiating price for a car" in new_context, \
        "Should include original context"
    
    # Verify continuation context marker
    assert "CONTINUATION CONTEXT" in new_context, \
        "Should include continuation context marker"
    
    # Verify last strategy is included
    assert "competitive" in new_context or "warranty" in new_context, \
        "Should include last strategy"
    
    # Verify recent transcript is included
    assert "What's your best offer?" in new_context, \
        "Should include recent transcript"
    
    logger.info("✓ Session handoff preserves conversation context")


@pytest.mark.asyncio
async def test_session_handoff_only_when_active():
    """
    Test that session handoff only occurs when session is ACTIVE
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start monitor_session_lifetime with session in ACTIVE state
    2. Change session state to ENDING before handoff trigger
    3. Verify handoff does not occur
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-handoff-inactive"
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Track session creation
    sessions_created = []
    
    async def mock_open_live_session(api_key: str, context: str):
        """Mock session creation"""
        sessions_created.append({"context": context})
        return MockLiveSessionForHandoff(session_id, is_new_session=True)
    
    # Mock asyncio.sleep
    original_sleep = asyncio.sleep
    
    async def fast_sleep(duration):
        if duration == SESSION_HANDOFF_TRIGGER:
            # Change session state before handoff
            logger.info("Changing session state to ENDING before handoff")
            session.state = NegotiationState.ENDING
            await original_sleep(0.1)
        else:
            await original_sleep(duration)
    
    # Execute with mocks
    with patch('asyncio.sleep', fast_sleep), \
         patch.object(GeminiClient, 'open_live_session', mock_open_live_session):
        
        # Start monitor_session_lifetime
        monitor_task = asyncio.create_task(
            GeminiClient.monitor_session_lifetime(session, mock_websocket, "test-api-key")
        )
        
        # Wait for monitor to complete
        await asyncio.sleep(0.5)
        
        # Task should complete naturally (not create new session)
        if not monitor_task.done():
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
    
    # Verify handoff did NOT occur
    assert len(sessions_created) == 0, \
        "Should not create new session when state is not ACTIVE"
    
    logger.info("✓ Session handoff only occurs when session is ACTIVE")


@pytest.mark.asyncio
async def test_session_handoff_recursive_monitoring():
    """
    Test that session handoff recursively schedules another monitor
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start monitor_session_lifetime
    2. Trigger first handoff
    3. Verify monitor_session_lifetime is called again
    4. This ensures continuous monitoring across multiple handoffs
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-handoff-recursive"
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Track monitor calls
    monitor_calls = []
    
    async def mock_open_live_session(api_key: str, context: str):
        """Mock session creation"""
        return MockLiveSessionForHandoff(session_id, is_new_session=True)
    
    # Mock asyncio.sleep
    original_sleep = asyncio.sleep
    sleep_call_count = 0
    
    async def fast_sleep(duration):
        nonlocal sleep_call_count
        if duration == SESSION_HANDOFF_TRIGGER:
            sleep_call_count += 1
            logger.info(f"Sleep called for handoff trigger (call #{sleep_call_count})")
            await original_sleep(0.1)
        else:
            await original_sleep(duration)
    
    # Track create_task calls
    original_create_task = asyncio.create_task
    monitor_tasks_created = []
    
    def track_create_task(coro):
        task = original_create_task(coro)
        # Check if this is a monitor_session_lifetime task
        if hasattr(coro, '__name__') and 'monitor_session_lifetime' in str(coro):
            monitor_tasks_created.append(task)
            logger.info(f"monitor_session_lifetime task created (total: {len(monitor_tasks_created)})")
        return task
    
    # Execute with mocks
    with patch('asyncio.sleep', fast_sleep), \
         patch('asyncio.create_task', track_create_task), \
         patch.object(GeminiClient, 'open_live_session', mock_open_live_session):
        
        # Start first monitor
        monitor_task = asyncio.create_task(
            GeminiClient.monitor_session_lifetime(session, mock_websocket, "test-api-key")
        )
        
        # Wait for first handoff and recursive monitor creation
        await asyncio.sleep(0.5)
        
        # Cancel all tasks
        monitor_task.cancel()
        for task in monitor_tasks_created:
            if not task.done():
                task.cancel()
        
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        for task in monitor_tasks_created:
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    # Verify recursive monitoring
    assert len(monitor_tasks_created) >= 1, \
        "Should create at least one recursive monitor task after handoff"
    
    logger.info("✓ Session handoff recursively schedules monitoring")
    logger.info(f"  - Monitor tasks created: {len(monitor_tasks_created)}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
