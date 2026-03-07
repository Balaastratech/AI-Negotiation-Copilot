from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
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
    
    # Outcome tracking
    initial_price: Optional[float] = None
    final_price: Optional[float] = None
    transcript: list[dict] = []
    strategy_history: list[dict] = []

    model_config = ConfigDict(
        arbitrary_types_allowed=True  # required for live_session handle
    )
