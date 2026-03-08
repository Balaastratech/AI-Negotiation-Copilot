"""
Preservation Property Tests for Continuous Conversation Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**

These tests verify that existing session lifecycle and message handling behaviors
are preserved when implementing the continuous conversation fix.

IMPORTANT: These tests MUST PASS on UNFIXED code to establish the baseline
behavior that must not regress when we implement the fix.

Testing Strategy:
- Observe behavior on UNFIXED code for non-buggy inputs
- Write property-based tests capturing observed behavior patterns
- Run tests on UNFIXED code - they should PASS
- After implementing fix, re-run tests to ensure no regressions
"""

import pytest
import asyncio
import logging
import json
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncIterator
from hypothesis import given, strategies as st, settings as hyp_settings

from app.services.gemini_client import GeminiClient, handle_gemini_text
from app.services.negotiation_engine import NegotiationEngine
from app.models.negotiation import NegotiationSession, NegotiationState

logger = logging.getLogger(__name__)


# ============================================================================
# Mock Classes for Testing
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
                audio_part.inline_data.data = b"fake_audio_data"
                audio_part.text = None
                self.model_turn.parts.append(audio_part)
            
            if has_text:
                text_part = MagicMock()
                text_part.inline_data = None
                text_part.text = has_text if isinstance(has_text, str) else "AI response text"
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


class MockLiveSessionWithError:
    """Mock session that raises an error during receive"""
    def __init__(self, error_to_raise):
        self.error_to_raise = error_to_raise
        
    async def receive(self) -> AsyncIterator[MockResponse]:
        # Yield one response then raise error
        yield MockResponse(MockServerContent(has_audio=True))
        raise self.error_to_raise


class MockLiveSessionNormal:
    """Mock session that yields one response then ends normally"""
    async def receive(self) -> AsyncIterator[MockResponse]:
        yield MockResponse(MockServerContent(has_audio=True, has_text=True))
        # Stream ends naturally


# ============================================================================
# Property 2: Preservation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_preservation_explicit_end_negotiation():
    """
    Property 2.1: Explicit END_NEGOTIATION cleanly closes session
    
    **Validates: Requirement 3.1**
    
    Test that when END_NEGOTIATION is sent, the system:
    - Transitions to ENDING state
    - Closes the Gemini Live session
    - Sends OUTCOME_SUMMARY
    - Transitions back to IDLE state
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session = NegotiationSession(session_id="test-end-123")
    session.state = NegotiationState.ACTIVE
    
    # Mock live session context manager
    mock_live_cm = AsyncMock()
    mock_live_cm.__aexit__ = AsyncMock()
    session.live_session_cm = mock_live_cm
    session.live_session = MagicMock()
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    
    # Execute END_NEGOTIATION
    payload = {"final_price": 100, "initial_price": 150}
    await NegotiationEngine.handle_end(session, payload, mock_websocket)
    
    # Verify behavior
    assert session.state == NegotiationState.IDLE, "Should transition to IDLE after ending"
    assert session.live_session is None, "Live session should be cleared"
    assert mock_live_cm.__aexit__.called, "Live session should be closed"
    
    # Verify OUTCOME_SUMMARY was sent
    outcome_messages = [m for m in messages_sent if m.get("type") == "OUTCOME_SUMMARY"]
    assert len(outcome_messages) == 1, "Should send OUTCOME_SUMMARY"
    assert outcome_messages[0]["payload"]["final_price"] == 100
    
    logger.info("✓ Preservation verified: Explicit END_NEGOTIATION cleanly closes session")


@pytest.mark.asyncio
async def test_preservation_stream_error_handling():
    """
    Property 2.2: Stream errors cause receive loop to exit and send AI_DEGRADED
    
    **Validates: Requirement 3.7**
    
    Test that when a stream error occurs, the system:
    - Exits the receive loop
    - Sends AI_DEGRADED message to frontend
    - Logs the error appropriately
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-error-123"
    
    # Create mock session that raises an error
    test_error = Exception("Simulated stream error")
    mock_live_session = MockLiveSessionWithError(test_error)
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = AsyncMock()
    
    # Execute receive_responses - should handle error gracefully
    session = NegotiationSession(session_id=session_id, state=NegotiationState.ACTIVE)
    await GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    
    # Verify AI_DEGRADED message was sent
    degraded_messages = [m for m in messages_sent if m.get("type") == "AI_DEGRADED"]
    assert len(degraded_messages) == 1, "Should send AI_DEGRADED on stream error"
    assert "interrupted" in degraded_messages[0]["payload"]["message"].lower() or \
           "recovery" in degraded_messages[0]["payload"]["message"].lower()
    
    logger.info("✓ Preservation verified: Stream errors handled correctly")


@pytest.mark.asyncio
async def test_preservation_cancellation_propagation():
    """
    Property 2.3: asyncio.CancelledError propagates correctly
    
    **Validates: Requirement 3.7**
    
    Test that when receive_responses is cancelled, the CancelledError
    propagates correctly without being caught or suppressed.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-cancel-123"
    
    # Create a mock session that blocks indefinitely so we can cancel it
    class MockLiveSessionBlocking:
        async def receive(self) -> AsyncIterator[MockResponse]:
            # Yield one response
            yield MockResponse(MockServerContent(has_audio=True))
            # Then block indefinitely
            await asyncio.sleep(10)
    
    mock_live_session = MockLiveSessionBlocking()
    
    mock_websocket.send_json = AsyncMock()
    mock_websocket.send_bytes = AsyncMock()
    
    # Start receive_responses task
    session = NegotiationSession(session_id=session_id, state=NegotiationState.ACTIVE)
    receive_task = asyncio.create_task(
        GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    )
    
    # Let it process the first response
    await asyncio.sleep(0.2)
    
    # Cancel the task while it's blocked
    receive_task.cancel()
    
    # Verify CancelledError is raised
    with pytest.raises(asyncio.CancelledError):
        await receive_task
    
    logger.info("✓ Preservation verified: CancelledError propagates correctly")


@pytest.mark.asyncio
async def test_preservation_audio_encoding():
    """
    Property 2.4: Audio encoding (16kHz PCM format) remains unchanged
    
    **Validates: Requirement 3.2**
    
    Test that audio chunks are encoded as 16kHz PCM format when sent
    to the Gemini Live API.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_live_session = AsyncMock()
    session_id = "test-audio-123"
    raw_pcm_bytes = b"\x00\x01\x02\x03" * 100  # Fake PCM data
    
    # Execute
    await GeminiClient.send_audio_chunk(mock_live_session, raw_pcm_bytes, session_id)
    
    # Verify
    assert mock_live_session.send_realtime_input.called, "Should call send_realtime_input"
    call_kwargs = mock_live_session.send_realtime_input.call_args.kwargs
    
    assert "audio" in call_kwargs, "Should send audio parameter"
    audio_blob = call_kwargs["audio"]
    assert audio_blob.mime_type == "audio/pcm;rate=16000", "Should use 16kHz PCM format"
    assert audio_blob.data == raw_pcm_bytes, "Should send raw PCM bytes"
    
    logger.info("✓ Preservation verified: Audio encoding is 16kHz PCM")


@pytest.mark.asyncio
async def test_preservation_transcription_messages():
    """
    Property 2.5: Transcription messages (TRANSCRIPT_UPDATE) are sent correctly
    
    **Validates: Requirement 3.4**
    
    Test that when transcription data is received from Gemini, the system
    sends TRANSCRIPT_UPDATE messages to the frontend for both user and AI.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-transcript-123"
    
    # Create mock session with transcriptions
    class MockLiveSessionWithTranscripts:
        def __init__(self, session):
            self.session = session
            
        async def receive(self) -> AsyncIterator[MockResponse]:
            # User transcription
            yield MockResponse(MockServerContent(
                input_transcription_text="User said this"
            ))
            # AI transcription
            yield MockResponse(MockServerContent(
                output_transcription_text="AI said this"
            ))
            # Change session state to stop the keep-alive loop
            self.session.state = NegotiationState.ENDING
    
    # Execute
    session = NegotiationSession(session_id=session_id, state=NegotiationState.ACTIVE)
    mock_live_session = MockLiveSessionWithTranscripts(session)
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = AsyncMock()
    
    # Execute receive_responses
    await GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    
    # Verify transcription messages
    transcript_messages = [m for m in messages_sent if m.get("type") == "TRANSCRIPT_UPDATE"]
    assert len(transcript_messages) == 2, "Should send 2 transcript updates"
    
    user_transcript = [m for m in transcript_messages if m["payload"]["speaker"] == "user"]
    ai_transcript = [m for m in transcript_messages if m["payload"]["speaker"] == "ai"]
    
    assert len(user_transcript) == 1, "Should have user transcript"
    assert user_transcript[0]["payload"]["text"] == "User said this"
    
    assert len(ai_transcript) == 1, "Should have AI transcript"
    assert ai_transcript[0]["payload"]["text"] == "AI said this"
    
    logger.info("✓ Preservation verified: Transcription messages sent correctly")


@pytest.mark.asyncio
async def test_preservation_strategy_update_parsing():
    """
    Property 2.6: Strategy update parsing and transmission works correctly
    
    **Validates: Requirement 3.5**
    
    Test that when AI text responses contain <strategy> tags, the system:
    - Parses the JSON strategy data
    - Sends STRATEGY_UPDATE messages
    - Sends remaining text as AI_RESPONSE
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-strategy-123"
    
    # Create text with strategy tags
    strategy_data = {"approach": "collaborative", "priority": "price"}
    text_with_strategy = f'<strategy>{json.dumps(strategy_data)}</strategy>Here is my advice'
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    
    # Execute
    await handle_gemini_text(mock_websocket, session_id, text_with_strategy)
    
    # Verify strategy update
    strategy_messages = [m for m in messages_sent if m.get("type") == "STRATEGY_UPDATE"]
    assert len(strategy_messages) == 1, "Should send STRATEGY_UPDATE"
    assert strategy_messages[0]["payload"] == strategy_data
    
    # Verify AI response with remaining text
    ai_messages = [m for m in messages_sent if m.get("type") == "AI_RESPONSE"]
    assert len(ai_messages) == 1, "Should send AI_RESPONSE"
    assert ai_messages[0]["payload"]["text"] == "Here is my advice"
    
    logger.info("✓ Preservation verified: Strategy update parsing works correctly")


@pytest.mark.asyncio
async def test_preservation_interruption_handling():
    """
    Property 2.7: Interruption messages are sent correctly
    
    **Validates: Requirement 2.5 (interruption handling preservation)**
    
    Test that when the AI is interrupted, the system sends
    AUDIO_INTERRUPTED message to the frontend.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-interrupt-123"
    
    # Create mock session with interruption
    class MockLiveSessionWithInterruption:
        def __init__(self, session):
            self.session = session
            
        async def receive(self) -> AsyncIterator[MockResponse]:
            # Normal response
            yield MockResponse(MockServerContent(has_audio=True))
            # Interruption
            yield MockResponse(MockServerContent(interrupted=True))
            # Continue after interruption
            yield MockResponse(MockServerContent(has_audio=True))
            # Change session state to stop the keep-alive loop
            self.session.state = NegotiationState.ENDING
    
    # Execute
    session = NegotiationSession(session_id=session_id, state=NegotiationState.ACTIVE)
    mock_live_session = MockLiveSessionWithInterruption(session)
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = AsyncMock()
    
    # Execute receive_responses
    await GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    
    # Verify interruption message
    interrupt_messages = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
    assert len(interrupt_messages) == 1, "Should send AUDIO_INTERRUPTED"
    
    logger.info("✓ Preservation verified: Interruption handling works correctly")


@pytest.mark.asyncio
async def test_preservation_vision_frame_processing():
    """
    Property 2.8: Vision frames are processed correctly
    
    **Validates: Requirement 3.6**
    
    Test that vision frames are sent to the Gemini Live API
    with correct JPEG encoding.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_live_session = AsyncMock()
    session_id = "test-vision-123"
    
    # Create fake base64 JPEG data
    import base64
    fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # JPEG header + data
    jpeg_base64 = base64.b64encode(fake_jpeg).decode('utf-8')
    
    # Execute
    await GeminiClient.send_vision_frame(mock_live_session, jpeg_base64, session_id)
    
    # Verify
    assert mock_live_session.send_realtime_input.called, "Should call send_realtime_input"
    call_kwargs = mock_live_session.send_realtime_input.call_args.kwargs
    
    assert "video" in call_kwargs, "Should send video parameter"
    video_blob = call_kwargs["video"]
    assert video_blob.mime_type == "image/jpeg", "Should use JPEG format"
    assert video_blob.data == fake_jpeg, "Should send decoded JPEG bytes"
    
    logger.info("✓ Preservation verified: Vision frame processing works correctly")


@pytest.mark.asyncio
async def test_preservation_message_validation():
    """
    Property 2.9: Message validation per state works correctly
    
    **Validates: Requirements 3.1, 3.8**
    
    Test that message validation correctly rejects invalid messages
    for each state and allows valid messages.
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    
    messages_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    mock_websocket.send_json = track_send_json
    
    # Test IDLE state - only PRIVACY_CONSENT_GRANTED allowed
    session_idle = NegotiationSession(session_id="test-idle")
    session_idle.state = NegotiationState.IDLE
    
    valid = await NegotiationEngine.validate_message(
        mock_websocket, session_idle, "PRIVACY_CONSENT_GRANTED"
    )
    assert valid, "PRIVACY_CONSENT_GRANTED should be valid in IDLE"
    
    invalid = await NegotiationEngine.validate_message(
        mock_websocket, session_idle, "START_NEGOTIATION"
    )
    assert not invalid, "START_NEGOTIATION should be invalid in IDLE"
    
    # Test CONSENTED state - only START_NEGOTIATION allowed
    session_consented = NegotiationSession(session_id="test-consented")
    session_consented.state = NegotiationState.CONSENTED
    
    valid = await NegotiationEngine.validate_message(
        mock_websocket, session_consented, "START_NEGOTIATION"
    )
    assert valid, "START_NEGOTIATION should be valid in CONSENTED"
    
    invalid = await NegotiationEngine.validate_message(
        mock_websocket, session_consented, "AUDIO_CHUNK"
    )
    assert not invalid, "AUDIO_CHUNK should be invalid in CONSENTED"
    
    # Test ACTIVE state - VISION_FRAME, AUDIO_CHUNK, END_NEGOTIATION allowed
    session_active = NegotiationSession(session_id="test-active")
    session_active.state = NegotiationState.ACTIVE
    
    valid = await NegotiationEngine.validate_message(
        mock_websocket, session_active, "AUDIO_CHUNK"
    )
    assert valid, "AUDIO_CHUNK should be valid in ACTIVE"
    
    valid = await NegotiationEngine.validate_message(
        mock_websocket, session_active, "END_NEGOTIATION"
    )
    assert valid, "END_NEGOTIATION should be valid in ACTIVE"
    
    logger.info("✓ Preservation verified: Message validation works correctly")


@pytest.mark.asyncio
async def test_preservation_state_transitions():
    """
    Property 2.10: State transitions work correctly
    
    **Validates: Requirement 3.8**
    
    Test that state transitions follow the correct flow:
    IDLE -> CONSENTED -> ACTIVE -> ENDING -> IDLE
    
    This behavior must be preserved after implementing the fix.
    """
    # Setup
    mock_websocket = AsyncMock()
    session = NegotiationSession(session_id="test-transitions")
    
    # Initial state
    assert session.state == NegotiationState.IDLE
    
    # IDLE -> CONSENTED
    await NegotiationEngine.transition_state(session, NegotiationState.CONSENTED, mock_websocket)
    assert session.state == NegotiationState.CONSENTED
    
    # CONSENTED -> ACTIVE
    await NegotiationEngine.transition_state(session, NegotiationState.ACTIVE, mock_websocket)
    assert session.state == NegotiationState.ACTIVE
    
    # ACTIVE -> ENDING
    await NegotiationEngine.transition_state(session, NegotiationState.ENDING, mock_websocket)
    assert session.state == NegotiationState.ENDING
    
    # ENDING -> IDLE
    await NegotiationEngine.transition_state(session, NegotiationState.IDLE, mock_websocket)
    assert session.state == NegotiationState.IDLE
    
    logger.info("✓ Preservation verified: State transitions work correctly")


# ============================================================================
# Property-Based Tests using Hypothesis
# ============================================================================

@given(
    has_audio=st.booleans(),
    has_text=st.booleans(),
    interrupted=st.booleans()
)
@hyp_settings(max_examples=50, deadline=None)
@pytest.mark.asyncio
async def test_preservation_property_all_response_types(has_audio, has_text, interrupted):
    """
    Property-Based Test: All response types are handled correctly
    
    **Validates: Requirements 3.3, 3.4**
    
    Generate random combinations of response types and verify they are
    all handled correctly without errors.
    
    This property must hold after implementing the fix.
    """
    # Skip if no content
    if not has_audio and not has_text and not interrupted:
        return
    
    # Setup
    mock_websocket = AsyncMock()
    session_id = "test-pbt-responses"
    
    class MockLiveSessionPBT:
        def __init__(self, session):
            self.session = session
            
        async def receive(self) -> AsyncIterator[MockResponse]:
            yield MockResponse(MockServerContent(
                has_audio=has_audio,
                has_text=has_text,
                interrupted=interrupted
            ))
            # Change session state to stop the keep-alive loop
            self.session.state = NegotiationState.ENDING
    
    # Execute - should not raise any errors
    session = NegotiationSession(session_id=session_id, state=NegotiationState.ACTIVE)
    mock_live_session = MockLiveSessionPBT(session)
    
    messages_sent = []
    audio_sent = []
    
    async def track_send_json(msg):
        messages_sent.append(msg)
    
    async def track_send_bytes(data):
        audio_sent.append(data)
    
    mock_websocket.send_json = track_send_json
    mock_websocket.send_bytes = track_send_bytes
    
    # Execute receive_responses - should not raise any errors
    await GeminiClient.receive_responses(mock_live_session, mock_websocket, session_id, session)
    
    # Verify appropriate messages were sent
    if interrupted:
        interrupt_msgs = [m for m in messages_sent if m.get("type") == "AUDIO_INTERRUPTED"]
        assert len(interrupt_msgs) > 0, "Should send AUDIO_INTERRUPTED when interrupted"
        # When interrupted, the function continues to next iteration, so audio/text may not be sent
        return
    
    if has_audio:
        assert len(audio_sent) > 0, "Should send audio bytes when has_audio"
    
    if has_text:
        text_msgs = [m for m in messages_sent if m.get("type") in ["AI_RESPONSE", "STRATEGY_UPDATE"]]
        assert len(text_msgs) > 0, "Should send text messages when has_text"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
