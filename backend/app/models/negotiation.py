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

    # Dual-Model: rolling audio buffer (shared between audio sender & listener)
    audio_buffer: Optional[Any] = None
    # Dual-Model: background listener agent task
    listener_agent: Optional[Any] = None

    # Flag strictly gating the Advisor's audio output (prevents random talking)
    advisor_active: bool = False

    # Context submitted via the SetupDialog (item, target_price, max_price, extra_context)
    user_context: dict = Field(default_factory=dict)

    # Lock that serializes ALL send_realtime_input calls for this session.
    # The Gemini Live SDK raises errors if audio and text are sent concurrently.
    gemini_send_lock: Any = Field(default_factory=asyncio.Lock)

    # Speaker identification (from voice fingerprinting)
    current_speaker: str = "user"  # "user" or "counterparty"
    speaker_last_updated: float = 0.0  # timestamp of last speaker update
    
    # Transcript buffering (for accurate speaker labeling)
    pending_transcripts: list[dict] = []  # Transcripts waiting for speaker confirmation
    
    # Outcome tracking
    initial_price: Optional[float] = None
    final_price: Optional[float] = None
    transcript: list[dict] = []
    strategy_history: list[dict] = []

    model_config = ConfigDict(
        arbitrary_types_allowed=True  # required for live_session handle and asyncio.Lock
    )
