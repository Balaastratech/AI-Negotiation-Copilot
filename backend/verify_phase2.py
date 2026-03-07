import sys
try:
    from app.models.negotiation import NegotiationSession, NegotiationState
    print('Models OK')
    from app.models.messages import ConsentPayload, StartNegotiationPayload, SessionStartedPayload
    print('Schemas OK')
    from app.services.connection_manager import ConnectionManager
    cm = ConnectionManager()
    print('ConnectionManager OK')
    from app.services.gemini_client import GeminiClient, GeminiUnavailableError
    print('GeminiClient OK')
    from app.services.gemini_client import SESSION_HANDOFF_TRIGGER
    assert SESSION_HANDOFF_TRIGGER == 540
    print('Monitor OK')
    from app.services.negotiation_engine import NegotiationEngine, VALID_MESSAGES
    print('Engine OK')
    from app.api.websocket import router
    print('WebSocket OK')
    from app.main import app
    print('App loads WebSocket OK')
except Exception as e:
    print("Verification failed:", e)
    sys.exit(1)
print("All verifications passed!")
