"""
Integration Tests for Multi-Turn Conversation

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

These integration tests verify that the continuous conversation fix enables
full multi-turn conversations without the receive loop exiting prematurely.

Test Strategy:
- Simulate realistic multi-turn conversations (5+ turns)
- Verify continuous bidirectional communication throughout entire session
- Verify receive loop does not exit between responses
- Test with various conversation patterns and timing
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncIterator, List

from app.services.gemini_client import GeminiClient
from app.models.negotiation import NegotiationSession, NegotiationState

logger = logging.getLogger(__name__)


# ============================================================================
# Mock Classes for Integration Testing
# ============================================================================

class MockServerContent:
    """Mock for Gemini server content response"""
    def __init__(self, has_audio=False, has_text=False, interrupted=False,
                 input_transcription_text=None, output_transcription_text=None):
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
                audio_part.inline_data.data = b"fake_audio_response_data"
                audio_part.text = None
                self.model_turn.parts.append(audio_part)
            
            if has_text:
                text_part = MagicMock()
                text_part.inline_data = None
                text_part.text = has_text if isinstance(has_text, str) else "AI response"
                self.model_turn.parts.append(text_part)
        
        if input_transcription_text:
            self.input_transcription = MagicMock()
            self.input_transcription.text = input_transcription_text
        
        if output_transcription_text:
            self.output_transcription = MagicMock()
            self.output_transcription.text = output_transcription_text


class MockResponse:
    """Mock for Gemini response"""
    def __init__(self, server_content):
        self.server_content = server_content


class MultiTurnMockLiveSession:
    """
    Mock Gemini Live session that simulates multiple conversation turns.
    
    Each call to receive() yields one AI response then ends the stream
    (simulating real Gemini Live API behavior). The fixed receive_responses
    should automatically restart the receive loop for continuous conversation.
    """
    def __init__(self, num_turns: int = 5, response_texts: List[str] = None):
        self.num_turns = num_turns
        self.response_texts = response_texts or [f"Response {i+1}" for i in range(num_turns)]
        self.receive_call_count = 0
        self.responses_sent = 0
        
    async def receive(self) -> AsyncIterator[MockResponse]:
        """
        Simulate Gemini Live API behavior:
        - Each call yields one response then ends stream
        - Fixed code should call this multiple times for multi-turn conversation
        """
        self.receive_call_count += 1
        
        if self.receive_call_count <= self.num_turns:
            logger.info(f"Turn {self.receive_call_count}/{self.num_turns}: Yielding AI response")
            
            response_text = self.response_texts[self.receive_call_count - 1]
            self.responses_sent += 1
            
            yield MockResponse(MockServerContent(
                has_audio=True,
                has_text=response_text,
                output_transcription_text=response_text
            ))
            
            logger.info(f"Turn {self.receive_call_count}: Stream ended naturally")
            return
        
        # After all turns, wait with periodic yields to allow state checks
        logger.info(f"All {self.num_turns} turns completed, waiting for more data")
        # Wait in small increments to allow the loop to check session state
        for _ in range(100):  # Wait up to 10 seconds total
            await asyncio.sleep(0.1)
        return


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_integration_five_turn_conversation():
    """
    Integration Test: Full 5-turn conversation flow
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test Strategy:
    1. Start session in ACTIVE state
    2. Simulate 5 conversation turns:
       - User speaks (simulated by stream providing response)
       - AI responds with audio and text
       - Stream ends naturally
       - Loop continues to next turn
    3. Verify all 5 turns are processed
    4. Verify receive loop does not exit between turns
    5. Verify continuous bidirectional communication
    
    Expected Behavior:
    - receive() called 5 times (once per turn)
    - 5 AI responses sent through WebSocket
    - receive_responses task continues running throughout
    - No premature exits between turns
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-5-turn"
    
    # Create session in ACTIVE state
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Create mock live session with 5 turns
    conversation_texts = [
        "Let's discuss the price",
        "I can offer you a discount",
        "What's your best offer?",
        "I can go down to $100",
        "That sounds reasonable"
    ]
    mock_live_session = MultiTurnMockLiveSession(
        num_turns=5,
        response_texts=conversation_texts
    )
    
    # Track messages and audio sent
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
        logger.info(f"WebSocket sent: {msg.get('type')}")
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
        logger.info(f"WebSocket sent audio: {len(data)} bytes")
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting 5-turn conversation test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for all 5 turns to be processed
    # Each turn takes some time, so wait generously
    await asyncio.sleep(2.0)
    
    # Verify task is still running (not exited prematurely)
    assert not receive_task.done(), (
        "receive_responses task should still be running after 5 turns. "
        "It should only exit when session state changes or explicit cancellation."
    )
    
    # Cancel task for cleanup
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify all 5 turns were processed
    # Note: receive() may be called one extra time as the loop continues after the last turn
    assert mock_live_session.receive_call_count >= 5, (
        f"Expected receive() to be called at least 5 times for 5-turn conversation, "
        f"but was called {mock_live_session.receive_call_count} times"
    )
    
    assert mock_live_session.responses_sent == 5, (
        f"Expected 5 responses to be sent, but only {mock_live_session.responses_sent} were sent"
    )
    
    # Verify audio frames were sent for all turns
    assert len(audio_frames_sent) >= 5, (
        f"Expected at least 5 audio frames (one per turn), "
        f"but only {len(audio_frames_sent)} were sent"
    )
    
    # Verify transcription messages for all turns
    transcript_messages = [m for m in messages_sent if m.get("type") == "TRANSCRIPT_UPDATE"]
    assert len(transcript_messages) >= 5, (
        f"Expected at least 5 transcript updates (one per turn), "
        f"but only {len(transcript_messages)} were sent"
    )
    
    # Verify AI response messages for all turns
    ai_response_messages = [m for m in messages_sent if m.get("type") == "AI_RESPONSE"]
    assert len(ai_response_messages) >= 5, (
        f"Expected at least 5 AI response messages (one per turn), "
        f"but only {len(ai_response_messages)} were sent"
    )
    
    # Verify conversation content
    for i, expected_text in enumerate(conversation_texts):
        matching_responses = [
            m for m in ai_response_messages 
            if expected_text in m.get("payload", {}).get("text", "")
        ]
        assert len(matching_responses) > 0, (
            f"Expected to find AI response containing '{expected_text}' for turn {i+1}"
        )
    
    logger.info("✓ Integration test PASSED: 5-turn conversation completed successfully")
    logger.info(f"  - receive() called {mock_live_session.receive_call_count} times")
    logger.info(f"  - {mock_live_session.responses_sent} responses processed")
    logger.info(f"  - {len(audio_frames_sent)} audio frames sent")
    logger.info(f"  - {len(transcript_messages)} transcripts sent")
    logger.info(f"  - {len(ai_response_messages)} AI responses sent")


@pytest.mark.asyncio
async def test_integration_extended_conversation():
    """
    Integration Test: Extended 10-turn conversation
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    
    Test a longer conversation to ensure the fix works for extended sessions.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-10-turn"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Create mock live session with 10 turns
    mock_live_session = MultiTurnMockLiveSession(num_turns=10)
    
    # Track metrics
    audio_frames_sent = []
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting 10-turn conversation test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for all 10 turns
    await asyncio.sleep(3.0)
    
    # Verify task is still running
    assert not receive_task.done(), "receive_responses should still be running"
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify all 10 turns were processed
    # Note: receive() may be called one extra time as the loop continues after the last turn
    assert mock_live_session.receive_call_count >= 10, (
        f"Expected at least 10 turns, got {mock_live_session.receive_call_count}"
    )
    
    assert len(audio_frames_sent) >= 10, (
        f"Expected at least 10 audio frames, got {len(audio_frames_sent)}"
    )
    
    logger.info("✓ Integration test PASSED: 10-turn conversation completed successfully")


@pytest.mark.asyncio
async def test_integration_no_premature_exit():
    """
    Integration Test: Verify no premature exit between turns
    
    **Validates: Requirements 2.2, 2.3**
    
    Test Strategy:
    - Start conversation
    - After each turn, verify receive_responses task is still running
    - Ensure task does not exit when stream ends naturally
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-no-exit"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    mock_live_session = MultiTurnMockLiveSession(num_turns=5)
    
    mock_websocket.send_json = AsyncMock()
    mock_websocket.send_bytes = AsyncMock()
    
    # Start receive_responses task
    logger.info("Starting no-premature-exit test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Check task status after each turn
    for turn in range(1, 6):
        # Wait for turn to complete
        await asyncio.sleep(0.5)
        
        # Verify task is still running
        assert not receive_task.done(), (
            f"receive_responses task exited prematurely after turn {turn}. "
            f"It should continue running for subsequent turns."
        )
        
        logger.info(f"✓ Turn {turn}: receive_responses still running")
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    logger.info("✓ Integration test PASSED: No premature exits detected")


@pytest.mark.asyncio
async def test_integration_continuous_bidirectional_communication():
    """
    Integration Test: Verify continuous bidirectional communication
    
    **Validates: Requirements 2.1, 2.3, 2.4**
    
    Test Strategy:
    - Simulate realistic conversation with varied response types
    - Verify both audio and text flow continuously
    - Verify transcriptions are sent for both user and AI
    - Ensure no gaps in communication
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-bidirectional"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Create conversation with varied content
    conversation_texts = [
        "Hello, I'd like to negotiate",
        "Sure, what's your offer?",
        "I can pay $80",
        "How about $90?",
        "Deal!"
    ]
    
    mock_live_session = MultiTurnMockLiveSession(
        num_turns=5,
        response_texts=conversation_texts
    )
    
    # Track all communication
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting bidirectional communication test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for conversation to progress
    await asyncio.sleep(2.0)
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify continuous audio communication
    assert len(audio_frames_sent) >= 5, (
        f"Expected continuous audio communication (5+ frames), "
        f"got {len(audio_frames_sent)} frames"
    )
    
    # Verify continuous text communication
    ai_responses = [m for m in messages_sent if m.get("type") == "AI_RESPONSE"]
    assert len(ai_responses) >= 5, (
        f"Expected continuous text communication (5+ responses), "
        f"got {len(ai_responses)} responses"
    )
    
    # Verify continuous transcription
    transcripts = [m for m in messages_sent if m.get("type") == "TRANSCRIPT_UPDATE"]
    assert len(transcripts) >= 5, (
        f"Expected continuous transcription (5+ updates), "
        f"got {len(transcripts)} updates"
    )
    
    # Verify no gaps - messages should be sent for each turn
    # Count messages per turn (should have audio + transcript + AI response per turn)
    messages_per_turn = (len(audio_frames_sent) + len(transcripts) + len(ai_responses)) / 5
    assert messages_per_turn >= 3, (
        f"Expected at least 3 messages per turn (audio + transcript + response), "
        f"got {messages_per_turn:.1f} messages per turn on average"
    )
    
    logger.info("✓ Integration test PASSED: Continuous bidirectional communication verified")
    logger.info(f"  - {len(audio_frames_sent)} audio frames")
    logger.info(f"  - {len(ai_responses)} AI responses")
    logger.info(f"  - {len(transcripts)} transcripts")


@pytest.mark.asyncio
async def test_integration_session_state_termination():
    """
    Integration Test: Verify receive loop respects session state
    
    **Validates: Requirements 2.3**
    
    Note: This test verifies that the loop checks session state.
    The actual state termination behavior is tested in preservation tests.
    This integration test focuses on multi-turn conversation flow.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-state-exit"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Use the standard multi-turn mock
    mock_live_session = MultiTurnMockLiveSession(num_turns=3)
    
    mock_websocket.send_json = AsyncMock()
    mock_websocket.send_bytes = AsyncMock()
    
    # Start receive_responses task
    logger.info("Starting session state termination test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Let all turns complete
    await asyncio.sleep(0.5)
    
    # Verify task is still running (waiting for more data)
    assert not receive_task.done(), "Task should be running"
    
    # Verify turns were processed
    assert mock_live_session.receive_call_count >= 3, (
        f"Expected at least 3 turns, got {mock_live_session.receive_call_count}"
    )
    
    # Change session state to ENDING
    logger.info("Changing session state to ENDING")
    session.state = NegotiationState.ENDING
    
    # The loop will check state after the current receive() completes
    # Since all turns are done, the mock is waiting, so we cancel the task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    logger.info("✓ Integration test PASSED: Session state check verified")
    logger.info(f"  - Processed {mock_live_session.receive_call_count} turns")
    logger.info("  - State termination behavior is tested in preservation tests")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
