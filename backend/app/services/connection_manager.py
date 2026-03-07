from typing import Optional, Dict, Any
from fastapi import WebSocket
import logging

from app.models.negotiation import NegotiationSession

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and negotiation sessions.
    
    Tracks all active sessions and provides methods to register, unregister,
    and retrieve session information.
    """
    
    def __init__(self):
        # Maps session_id -> {"websocket": WebSocket, "session": NegotiationSession}
        self.active_connections: Dict[str, Dict[str, Any]] = {}
    
    async def register(
        self,
        websocket: WebSocket,
        session_id: str,
        session: NegotiationSession
    ) -> None:
        """Register a new WebSocket connection with a session.
        
        Args:
            websocket: The WebSocket connection
            session_id: Unique session identifier
            session: The NegotiationSession object
        """
        self.active_connections[session_id] = {
            "websocket": websocket,
            "session": session
        }
        logger.info(f"Registered connection for session: {session_id}")
    
    async def unregister(self, session_id: str) -> None:
        """Unregister a session and close its Gemini session if open.
        
        Args:
            session_id: The session to unregister
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to unregister non-existent session: {session_id}")
            return
        
        connection_data = self.active_connections[session_id]
        session: NegotiationSession = connection_data["session"]
        
        # Close Gemini session if it's open
        if session.live_session is not None:
            try:
                await self._close_gemini_session(session)
            except Exception as e:
                logger.error(f"Error closing Gemini session for {session_id}: {e}")
        
        # Remove from active connections
        del self.active_connections[session_id]
        logger.info(f"Unregistered session: {session_id}")
    
    async def _close_gemini_session(self, session: NegotiationSession) -> None:
        """Close the Gemini Live session if open.
        
        Args:
            session: The NegotiationSession with live_session to close
        """
        if session.live_session is not None:
            try:
                # Attempt to close the Gemini session gracefully
                # The exact method depends on the Gemini SDK being used
                if hasattr(session.live_session, 'close'):
                    await session.live_session.close()
                elif hasattr(session.live_session, 'aio') and hasattr(session.live_session.aio, 'close'):
                    await session.live_session.aio.close()
                logger.info(f"Closed Gemini session for {session.session_id}")
            except Exception as e:
                logger.warning(f"Error during Gemini session close: {e}")
            finally:
                session.live_session = None
    
    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get the NegotiationSession for a given session_id.
        
        Args:
            session_id: The session identifier
            
        Returns:
            The NegotiationSession if found, None otherwise
        """
        connection_data = self.active_connections.get(session_id)
        if connection_data:
            return connection_data["session"]
        return None
    
    def get_websocket(self, session_id: str) -> Optional[WebSocket]:
        """Get the WebSocket for a given session_id.
        
        Args:
            session_id: The session identifier
            
        Returns:
            The WebSocket if found, None otherwise
        """
        connection_data = self.active_connections.get(session_id)
        if connection_data:
            return connection_data["websocket"]
        return None
    
    def get_all_sessions(self) -> Dict[str, NegotiationSession]:
        """Get all active sessions.
        
        Returns:
            Dictionary mapping session_id to NegotiationSession
        """
        return {
            sid: data["session"] 
            for sid, data in self.active_connections.items()
        }
    
    @property
    def active_session_count(self) -> int:
        """Get the count of active sessions."""
        return len(self.active_connections)


# Singleton instance for use across the application
connection_manager = ConnectionManager()
