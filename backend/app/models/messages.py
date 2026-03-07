from typing import Optional
from pydantic import BaseModel


# =============================================================================
# Client → Server Messages (Text Frames / JSON)
# =============================================================================

class ConsentPayload(BaseModel):
    """Payload for PRIVACY_CONSENT_GRANTED message."""
    version: str
    mode: str  # "live" or "roleplay"


class StartNegotiationPayload(BaseModel):
    """Payload for START_NEGOTIATION message."""
    context: str  # user-provided description of negotiation situation


class VisionFramePayload(BaseModel):
    """Payload for VISION_FRAME message."""
    image: str  # base64-encoded JPEG
    timestamp: int  # Unix milliseconds


class EndNegotiationPayload(BaseModel):
    """Payload for END_NEGOTIATION message."""
    final_price: Optional[float] = None  # agreed final price (null if no deal)
    initial_price: Optional[float] = None  # original asking price


class TranscriptEntry(BaseModel):
    """Transcript entry for TRANSCRIPT_UPDATE."""
    id: str  # unique ID with txn_ prefix
    speaker: str  # "user" | "counterparty" | "ai"
    text: str
    timestamp: int  # Unix milliseconds


class StrategyUpdate(BaseModel):
    """Strategy update payload for STRATEGY_UPDATE."""
    target_price: Optional[float] = None
    current_offer: Optional[float] = None
    recommended_response: str
    key_points: list[str]
    approach_type: str  # "aggressive" | "collaborative" | "walkaway"
    confidence: float
    walkaway_threshold: Optional[float] = None
    web_search_used: bool
    search_sources: list[str]


class OutcomeSummary(BaseModel):
    """Outcome summary for OUTCOME_SUMMARY."""
    deal_reached: bool
    initial_price: Optional[float] = None
    final_price: Optional[float] = None
    savings: Optional[float] = None
    savings_percentage: Optional[float] = None
    market_value: Optional[float] = None
    vs_market: Optional[float] = None
    negotiation_duration_seconds: int
    key_moves: list[str]
    effectiveness_score: float
    transcript_summary: str


# =============================================================================
# Server → Client Messages (Text Frames / JSON)
# =============================================================================

class ConnectionEstablishedPayload(BaseModel):
    """Payload for CONNECTION_ESTABLISHED."""
    session_id: str
    server_time: int


class ConsentAcknowledgedPayload(BaseModel):
    """Payload for CONSENT_ACKNOWLEDGED."""
    mode: str
    recording_active: bool


class SessionStartedPayload(BaseModel):
    """Payload for SESSION_STARTED."""
    session_id: str
    model: str
    features: dict  # {"audio": bool, "vision": bool, "web_search": bool}


class TranscriptUpdatePayload(BaseModel):
    """Payload for TRANSCRIPT_UPDATE."""
    id: str
    speaker: str
    text: str
    timestamp: int


class StrategyUpdatePayload(BaseModel):
    """Payload for STRATEGY_UPDATE."""
    target_price: Optional[float] = None
    current_offer: Optional[float] = None
    recommended_response: str
    key_points: list[str]
    approach_type: str
    confidence: float
    walkaway_threshold: Optional[float] = None
    web_search_used: bool
    search_sources: list[str]


class AIResponsePayload(BaseModel):
    """Payload for AI_RESPONSE."""
    text: str
    response_type: str  # "analysis" | "coaching" | "alert" | "summary"
    timestamp: int


class AudioInterruptedPayload(BaseModel):
    """Payload for AUDIO_INTERRUPTED."""
    pass  # Empty payload


class SessionReconnectingPayload(BaseModel):
    """Payload for SESSION_RECONNECTING."""
    reason: str  # "gemini_session_dropped" | "session_timeout" | "model_fallback"
    attempt: int
    max_attempts: int


class AIDegradedPayload(BaseModel):
    """Payload for AI_DEGRADED."""
    message: str
    features_available: list[str]


class ErrorPayload(BaseModel):
    """Payload for ERROR messages."""
    code: str
    message: str
