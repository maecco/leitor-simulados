"""
Session Manager Service
Handles user sessions and image storage
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from threading import Lock

from core.definitions.enums import TestType


@dataclass
class Session:
    """Represents a user session"""
    session_id: str
    test_type: TestType
    created_at: datetime
    images: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "test_type": self.test_type.name,
            "created_at": self.created_at.isoformat(),
            "image_count": len(self.images),
            "processed_count": sum(1 for img in self.images.values() if img.get("processed", False))
        }


class SessionManager:
    """
    Manages user sessions for the web application.
    Each session can have multiple images and maintains processing state.
    """
    
    # Session timeout in hours
    SESSION_TIMEOUT_HOURS = 24
    
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = Lock()
    
    def create_session(self, test_type: TestType) -> str:
        """Create a new session and return its ID"""
        session_id = str(uuid.uuid4())
        
        with self._lock:
            self._sessions[session_id] = Session(
                session_id=session_id,
                test_type=test_type,
                created_at=datetime.now()
            )
        
        # Cleanup old sessions
        self._cleanup_expired_sessions()
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Check if session is expired
                if self._is_expired(session):
                    self._delete_session_internal(session_id)
                    return None
            return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and cleanup its resources"""
        with self._lock:
            return self._delete_session_internal(session_id)
    
    def _delete_session_internal(self, session_id: str) -> bool:
        """Internal method to delete session (must be called with lock held)"""
        if session_id in self._sessions:
            # Cleanup image data
            session = self._sessions[session_id]
            session.images.clear()
            del self._sessions[session_id]
            return True
        return False
    
    def add_image(self, session_id: str, filename: str, image_bytes: bytes) -> Optional[str]:
        """Add an image to a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            
            image_id = str(uuid.uuid4())
            session.images[image_id] = {
                "filename": filename,
                "raw": image_bytes,
                "processed": False,
                "processed_image": None,
                "detections": None,
                "blocks": None,
                "report": None
            }
            return image_id
    
    def get_image(self, session_id: str, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image data from a session"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None
            return session.images.get(image_id)
    
    def update_image_results(
        self,
        session_id: str,
        image_id: str,
        processed_image: bytes = None,
        detections: list = None,
        blocks = None,
        report = None
    ) -> bool:
        """Update image with processing results"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session or image_id not in session.images:
                return False
            
            img_data = session.images[image_id]
            img_data["processed"] = True
            
            if processed_image is not None:
                img_data["processed_image"] = processed_image
            if detections is not None:
                img_data["detections"] = detections
            if blocks is not None:
                img_data["blocks"] = blocks
            if report is not None:
                img_data["report"] = report
            
            return True
    
    def _is_expired(self, session: Session) -> bool:
        """Check if a session has expired"""
        expiry_time = session.created_at + timedelta(hours=self.SESSION_TIMEOUT_HOURS)
        return datetime.now() > expiry_time
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired = [
            sid for sid, session in self._sessions.items()
            if self._is_expired(session)
        ]
        for sid in expired:
            self._delete_session_internal(sid)
    
    def cleanup_all(self):
        """Cleanup all sessions"""
        with self._lock:
            for session in self._sessions.values():
                session.images.clear()
            self._sessions.clear()
    
    def get_all_sessions(self) -> list[dict]:
        """Get info about all active sessions"""
        with self._lock:
            return [session.to_dict() for session in self._sessions.values()]
