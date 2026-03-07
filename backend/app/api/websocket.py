import uuid
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.connection_manager import connection_manager
from app.models.negotiation import NegotiationSession
from app.services.negotiation_engine import NegotiationEngine

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    session = NegotiationSession(session_id=session_id)
    
    await websocket.accept()
    await connection_manager.register(websocket, session_id, session)
    
    await websocket.send_json({
        "type": "CONNECTION_ESTABLISHED",
        "payload": {
            "session_id": session_id,
            "server_time": 0
        }
    })
    
    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                if not await NegotiationEngine.validate_message(websocket, session, "AUDIO_CHUNK"):
                    continue
                await NegotiationEngine.handle_audio_chunk(session, message["bytes"])
                
            elif "text" in message and message["text"]:
                data = json.loads(message["text"])
                msg_type = data.get("type", "UNKNOWN")
                
                if not await NegotiationEngine.validate_message(websocket, session, msg_type):
                    continue
                
                await NegotiationEngine.route_message(websocket, session, msg_type, data.get("payload", {}))
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected [session={session_id}]")
    except Exception as e:
        logger.error(f"WebSocket error [session={session_id}]: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "ERROR",
                "payload": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
            })
        except Exception:
            pass
    finally:
        await connection_manager.unregister(session_id)
