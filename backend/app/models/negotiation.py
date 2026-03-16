from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field
import asyncio
import time


class NegotiationState(str, Enum):
    """State machine states for negotiation sessions."""
    IDLE = "IDLE"
    CONSENTED = "CONSENTED"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"


class NegotiationSession(BaseModel):
    """Model representing a negotiation session.
    
    Tracks session state, consent information, and negotiation data
    including transcript and strategy history.
    """
    session_id: str
    state: NegotiationState = NegotiationState.IDLE
    consent_version: Optional[str] = None
    consent_mode: Optional[str] = None  # "live" or "roleplay"
    started_at: Optional[float] = None  # unix timestamp
    context: str = ""  # negotiation context string
    
    # Gemini Live session handle (not serialized - runtime only)
    live_session: Optional[Any] = None
    # Async context manager returned by open_live_session – kept so __aexit__ can be called on end
    live_session_cm: Optional[Any] = None
    # API key stored for auto-reconnect on 1007 codec errors
    api_key: Optional[str] = None

    # Dual-Model: rolling audio buffer (shared between audio sender & listener)
    audio_buffer: Optional[Any] = None
    # Dual-Model: background listener agent task
    listener_agent: Optional[Any] = None

    # Flag — True only during deliberate long-press window; gates mic audio to Live AI
    user_addressing_ai: bool = False
    # Flag — True after user presses Start Copilot; persists for the whole negotiation
    copilot_active: bool = False
    
    # AI speaking state - used to pause intel injections while AI is generating audio
    ai_is_speaking: bool = False
    # Queue for intel injections that were skipped while AI was speaking
    pending_injections: list = Field(default_factory=list)
    
    # Stores the last transcribed text from the user's direct address to the AI
    last_user_transcript: str = ""
    # Set True when user releases long-press so receive_responses knows the next
    # turn_complete is from a direct user query — prevents flush_pending_injections
    # from firing and triggering a second proactive AI response.
    direct_query_in_flight: bool = False
    
    # Accumulates AI response text for validation at turn_complete
    current_ai_response: str = ""

    # Response mode for AI responses (set by Get Advice / Get Command buttons)
    # "advice" = skip validation, "command" = apply validation
    response_mode: str = "command"

    # Context submitted via the SetupDialog (item, target_price, max_price, extra_context)
    user_context: dict = Field(default_factory=dict)

    # Lock that serializes ALL send_realtime_input calls for this session.
    # The Gemini Live SDK raises errors if audio and text are sent concurrently.
    gemini_send_lock: Any = Field(default_factory=asyncio.Lock)

    # Speaker identification (manual selection only)
    current_speaker: str = "unknown"  # "user", "counterparty", or "unknown"
    manual_override_until: Optional[float] = None # Timestamp until which auto-recognition is paused
    speaker_last_updated: float = 0.0  # timestamp of last speaker update
    # Timeline of speaker changes: [{speaker, timestamp}] — used by ListenerAgent for per-window attribution
    speaker_timeline: list = Field(default_factory=list)
    # Speaker mapping for Gemini diarization: {"Speaker 1": "user", "Speaker 2": "counterparty"}
    speaker_mapping: dict = Field(default_factory=dict)
    
    # Transcript buffering (for accurate speaker labeling)
    pending_transcripts: list[dict] = []  # Transcripts waiting for speaker confirmation

    # Speaker segment tracking — who is speaking NOW (set on button click)
    speaker_segment_start: float = 0.0      # kept for manual_mode guard only
    speaker_segment_speaker: str = "unknown"

    # Direct audio accumulation for the current speaker turn.
    # Audio is appended here on every AUDIO_CHUNK while this speaker is active.
    # On the NEXT button click the buffer is extracted and transcribed with the
    # PREVIOUS speaker label — no timestamp arithmetic, no clock-drift issues.
    current_segment_audio: bytes = b""

    # Captures raw PCM audio while user holds the "Ask AI" button.
    # Transcribed to text on button release for reliable Live AI question answering.
    # Audio is NOT pushed to the listener buffer during this window.
    question_capture_bytes: bytes = b""

    # Outcome tracking
    initial_price: Optional[float] = None
    final_price: Optional[float] = None
    transcript: list[dict] = []
    strategy_history: list[dict] = []

    model_config = ConfigDict(
        arbitrary_types_allowed=True  # required for live_session handle and asyncio.Lock
    )
