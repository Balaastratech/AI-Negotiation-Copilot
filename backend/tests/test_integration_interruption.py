"""
Integration Tests for Interruption Handling

**Validates: Requirements 2.5, 2.6**

These integration tests verify that the continuous conversation fix properly
handles interruptions during AI responses, ensuring the conversation continues
after an interruption.

Test Strategy:
- Simulate interruption flow: user speaks → AI responds → user interrupts → conversation continues
- Verify AUDIO_INTERRUPTED message is sent
- Verify receive loop continues listening after interruption
- Verify subsequent user input is processed correctly
- Test various interruption scenarios and timing
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
# Mock Classes for Interruption Testing
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


class InterruptionMockLiveSession:
    """
    Mock Gemini Live session that simulates interruption scenarios.
    
    Simulates:
    1. User speaks → AI starts responding
    2. User interrupts mid-response
    3. AI handles interruption (interrupted flag)
    4. Conversation continues with new user input
    """
    def __init__(self, interruption_pattern: List[str]):
        """
        Args:
            interruption_pattern: List describing the conversation flow
                - "response": Normal AI response
                - "interrupt": Interruption event
                - "continue": Response after interruption
        """
        self.interruption_pattern = interruption_pattern
        self.receive_call_count = 0
        self.responses_sent = 0
        self.interruptions_sent = 0
        
    async def receive(self) -> AsyncIterator[MockResponse]:
        """
        Simulate Gemini Live API behavior with interruptions.
        Each call to receive() processes one segment of the pattern.
        """
        self.receive_call_count += 1
        
        if self.receive_call_count <= len(self.interruption_pattern):
            event_type = self.interruption_pattern[self.receive_call_count - 1]
            
            if event_type == "response":
                logger.info(f"Call {self.receive_call_count}: Yielding normal AI response")
                self.responses_sent += 1
                yield MockResponse(MockServerContent(
                    has_audio=True,
                    has_text=f"Response {self.responses_sent}",
                    output_transcription_text=f"Response {self.responses_sent}"
                ))
                
            elif event_type == "interrupt":
                logger.info(f"Call {self.receive_call_count}: Yielding interruption event")
                self.interruptions_sent += 1
                # First yield the interruption flag
                yield MockResponse(MockServerContent(interrupted=True))
                # Then yield the new user input response
                self.responses_sent += 1
                yield MockResponse(MockServerContent(
                    has_audio=True,
                    has_text=f"Response after interrupt {self.interruptions_sent}",
                    output_transcription_text=f"Response after interrupt {self.interruptions_sent}"
                ))
                
            elif event_type == "continue":
                logger.info(f"Call {self.receive_call_count}: Yielding continuation response")
                self.responses_sent += 1
                yield MockResponse(MockServerContent(
                    has_audio=True,
                    has_text=f"Continuation {self.responses_sent}",
                    output_transcription_text=f"Continuation {self.responses_sent}"
                ))
            
            logger.info(f"Call {self.receive_call_count}: Stream ended naturally")
            return
        
        # After pattern completes, wait for more data
        logger.info(f"Pattern completed, waiting for more data")
        for _ in range(100):
            await asyncio.sleep(0.1)
        return


# ============================================================================
# Integration Tests for Interruption Handling
# ============================================================================

@pytest.mark.asyncio
async def test_integration_single_interruption():
    """
    Integration Test: Single interruption during AI response
    
    **Validates: Requirements 2.5, 2.6**
    
    Test Flow:
    1. User speaks → AI starts responding
    2. User interrupts mid-response
    3. System sends AUDIO_INTERRUPTED message
    4. System processes new user input
    5. AI provides new response
    6. Conversation continues normally
    
    Expected Behavior:
    - AUDIO_INTERRUPTED message sent when interruption occurs
    - receive loop continues after interruption
    - Subsequent user input is processed
    - No premature exit of receive loop
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-single-interrupt"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern: response → interrupt → continue
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["response", "interrupt", "continue"]
    )
    
    # Track messages and audio
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
    logger.info("Starting single interruption test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(1.5)
    
    # Verify task is still running (not exited after interruption)
    assert not receive_task.done(), (
        "receive_responses task should still be running after interruption. "
        "Interruptions should not cause the loop to exit."
    )
    
    # Cancel task for cleanup
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify AUDIO_INTERRUPTED message was sent
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 1, (
        f"Expected 1 AUDIO_INTERRUPTED message, got {len(interrupt_messages)}"
    )
    
    # Verify receive loop continued after interruption
    assert mock_live_session.receive_call_count >= 3, (
        f"Expected receive() to be called at least 3 times (response + interrupt + continue), "
        f"but was called {mock_live_session.receive_call_count} times"
    )
    
    # Verify responses were sent after interruption
    assert mock_live_session.responses_sent >= 2, (
        f"Expected at least 2 responses (before and after interrupt), "
        f"got {mock_live_session.responses_sent}"
    )
    
    # Verify audio frames were sent after interruption
    assert len(audio_frames_sent) >= 2, (
        f"Expected at least 2 audio frames (before and after interrupt), "
        f"got {len(audio_frames_sent)}"
    )
    
    # Verify AI responses were sent after interruption
    ai_responses = [m for m in messages_sent if m.get("type") == "AI_RESPONSE"]
    assert len(ai_responses) >= 2, (
        f"Expected at least 2 AI responses (before and after interrupt), "
        f"got {len(ai_responses)}"
    )
    
    logger.info("✓ Integration test PASSED: Single interruption handled correctly")
    logger.info(f"  - {mock_live_session.interruptions_sent} interruption(s) detected")
    logger.info(f"  - {mock_live_session.responses_sent} responses sent")
    logger.info(f"  - {len(interrupt_messages)} AUDIO_INTERRUPTED message(s) sent")
    logger.info(f"  - Conversation continued after interruption")


@pytest.mark.asyncio
async def test_integration_multiple_interruptions():
    """
    Integration Test: Multiple interruptions during conversation
    
    **Validates: Requirements 2.5, 2.6**
    
    Test Flow:
    1. Normal response
    2. First interruption
    3. Response after first interruption
    4. Second interruption
    5. Response after second interruption
    6. Normal continuation
    
    Expected Behavior:
    - Multiple AUDIO_INTERRUPTED messages sent
    - receive loop continues after each interruption
    - All subsequent inputs are processed
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-multiple-interrupts"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern: response → interrupt → response → interrupt → continue
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["response", "interrupt", "response", "interrupt", "continue"]
    )
    
    # Track messages
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting multiple interruptions test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(2.5)
    
    # Verify task is still running
    assert not receive_task.done(), (
        "receive_responses should still be running after multiple interruptions"
    )
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify multiple AUDIO_INTERRUPTED messages
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 2, (
        f"Expected 2 AUDIO_INTERRUPTED messages, got {len(interrupt_messages)}"
    )
    
    # Verify all pattern events were processed
    assert mock_live_session.receive_call_count >= 5, (
        f"Expected receive() to be called at least 5 times, "
        f"got {mock_live_session.receive_call_count}"
    )
    
    # Verify responses continued after each interruption
    assert mock_live_session.responses_sent >= 3, (
        f"Expected at least 3 responses (initial + after each interrupt), "
        f"got {mock_live_session.responses_sent}"
    )
    
    logger.info("✓ Integration test PASSED: Multiple interruptions handled correctly")
    logger.info(f"  - {mock_live_session.interruptions_sent} interruptions detected")
    logger.info(f"  - {mock_live_session.responses_sent} responses sent")
    logger.info(f"  - {len(interrupt_messages)} AUDIO_INTERRUPTED messages sent")


@pytest.mark.asyncio
async def test_integration_interruption_then_multi_turn():
    """
    Integration Test: Interruption followed by multi-turn conversation
    
    **Validates: Requirements 2.5, 2.6**
    
    Test Flow:
    1. Normal response
    2. Interruption
    3. Multiple normal turns after interruption
    
    Expected Behavior:
    - Interruption handled correctly
    - Conversation continues normally after interruption
    - Multiple turns work after interruption
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-interrupt-then-multi"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern: response → interrupt → 3 normal responses
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["response", "interrupt", "continue", "continue", "continue"]
    )
    
    # Track messages
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting interruption then multi-turn test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(2.5)
    
    # Verify task is still running
    assert not receive_task.done(), (
        "receive_responses should still be running after interruption and multi-turn"
    )
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify interruption was handled
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 1, (
        f"Expected 1 AUDIO_INTERRUPTED message, got {len(interrupt_messages)}"
    )
    
    # Verify all turns were processed
    assert mock_live_session.receive_call_count >= 5, (
        f"Expected receive() to be called at least 5 times, "
        f"got {mock_live_session.receive_call_count}"
    )
    
    # Verify multiple responses after interruption
    assert mock_live_session.responses_sent >= 4, (
        f"Expected at least 4 responses (1 before + 3 after interrupt), "
        f"got {mock_live_session.responses_sent}"
    )
    
    # Verify audio frames for all responses
    assert len(audio_frames_sent) >= 4, (
        f"Expected at least 4 audio frames, got {len(audio_frames_sent)}"
    )
    
    logger.info("✓ Integration test PASSED: Multi-turn conversation after interruption")
    logger.info(f"  - 1 interruption handled")
    logger.info(f"  - {mock_live_session.responses_sent} total responses")
    logger.info(f"  - Conversation continued normally after interruption")


@pytest.mark.asyncio
async def test_integration_immediate_interruption():
    """
    Integration Test: Immediate interruption at start of response
    
    **Validates: Requirements 2.5, 2.6**
    
    Test Flow:
    1. AI starts responding
    2. Immediate interruption (user speaks right away)
    3. Conversation continues
    
    Expected Behavior:
    - Interruption handled even at start of response
    - No audio queue issues
    - Conversation continues normally
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-immediate-interrupt"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern: immediate interrupt → continue
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["interrupt", "continue", "continue"]
    )
    
    # Track messages
    messages_sent = []
    audio_frames_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_frames_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Start receive_responses task
    logger.info("Starting immediate interruption test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(1.5)
    
    # Verify task is still running
    assert not receive_task.done(), (
        "receive_responses should still be running after immediate interruption"
    )
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify interruption was handled
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 1, (
        f"Expected 1 AUDIO_INTERRUPTED message, got {len(interrupt_messages)}"
    )
    
    # Verify conversation continued after immediate interruption
    assert mock_live_session.responses_sent >= 2, (
        f"Expected at least 2 responses after immediate interrupt, "
        f"got {mock_live_session.responses_sent}"
    )
    
    logger.info("✓ Integration test PASSED: Immediate interruption handled correctly")


@pytest.mark.asyncio
async def test_integration_interruption_with_transcription():
    """
    Integration Test: Interruption with transcription updates
    
    **Validates: Requirements 2.5, 2.6**
    
    Test Flow:
    1. Normal response with transcription
    2. Interruption
    3. Response after interruption with transcription
    
    Expected Behavior:
    - AUDIO_INTERRUPTED message sent
    - Transcriptions continue to work after interruption
    - All messages flow correctly
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-interrupt-transcript"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern with transcriptions
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["response", "interrupt", "continue"]
    )
    
    # Track messages
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = AsyncMock()
    
    # Start receive_responses task
    logger.info("Starting interruption with transcription test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(1.5)
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify interruption message
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 1, (
        f"Expected 1 AUDIO_INTERRUPTED message, got {len(interrupt_messages)}"
    )
    
    # Verify transcriptions were sent
    transcript_messages = [m for m in messages_sent if m.get("type") == "TRANSCRIPT_UPDATE"]
    assert len(transcript_messages) >= 2, (
        f"Expected at least 2 transcript updates (before and after interrupt), "
        f"got {len(transcript_messages)}"
    )
    
    # Verify AI responses were sent
    ai_responses = [m for m in messages_sent if m.get("type") == "AI_RESPONSE"]
    assert len(ai_responses) >= 2, (
        f"Expected at least 2 AI responses (before and after interrupt), "
        f"got {len(ai_responses)}"
    )
    
    logger.info("✓ Integration test PASSED: Interruption with transcription works correctly")
    logger.info(f"  - {len(interrupt_messages)} AUDIO_INTERRUPTED message")
    logger.info(f"  - {len(transcript_messages)} transcript updates")
    logger.info(f"  - {len(ai_responses)} AI responses")


@pytest.mark.asyncio
async def test_integration_no_false_interruptions():
    """
    Integration Test: Verify no false interruption detection
    
    **Validates: Requirements 2.5**
    
    Test Flow:
    1. Multiple normal responses without interruptions
    2. Verify no AUDIO_INTERRUPTED messages sent
    
    Expected Behavior:
    - No false interruption detection
    - Only real interruptions trigger AUDIO_INTERRUPTED
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "integration-no-false-interrupts"
    
    session = NegotiationSession(session_id=session_id)
    session.state = NegotiationState.ACTIVE
    
    # Pattern: all normal responses, no interruptions
    mock_live_session = InterruptionMockLiveSession(
        interruption_pattern=["response", "response", "response", "response"]
    )
    
    # Track messages
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = AsyncMock()
    
    # Start receive_responses task
    logger.info("Starting no false interruptions test")
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Wait for pattern to complete
    await asyncio.sleep(2.0)
    
    # Cancel task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    # Verify NO interruption messages were sent
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 0, (
        f"Expected 0 AUDIO_INTERRUPTED messages (no interruptions), "
        f"but got {len(interrupt_messages)}"
    )
    
    # Verify all responses were processed normally
    assert mock_live_session.responses_sent == 4, (
        f"Expected 4 responses, got {mock_live_session.responses_sent}"
    )
    
    logger.info("✓ Integration test PASSED: No false interruption detection")
    logger.info(f"  - {mock_live_session.responses_sent} responses processed")
    logger.info(f"  - 0 false interruptions detected")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
