"""
Session Router
Handles session creation, retrieval, and deletion
"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Form, status

from core.definitions.enums import TestType
from dependencies import (
    SessionManagerDep,
    ValidSessionDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/session/create", response_model=Dict[str, str])
async def create_session(
    test_type: str = Form(...),
    session_manager: SessionManagerDep = None
) -> Dict[str, str]:
    """Create a new processing session"""
    try:
        test_type_enum = TestType[test_type]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid test type: {test_type}. Valid types: {[t.name for t in TestType if t != TestType.NULL]}"
        )
    
    session_id = session_manager.create_session(test_type_enum)
    logger.info(f"Created session {session_id} with type {test_type}")
    
    return {"session_id": session_id, "test_type": test_type}


@router.get("/session/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session: ValidSessionDep
) -> Dict[str, Any]:
    """Get session information"""
    return session.to_dict()


@router.delete("/session/{session_id}", response_model=Dict[str, str])
async def delete_session(
    session_id: str,
    session_manager: SessionManagerDep
) -> Dict[str, str]:
    """Delete a session and cleanup resources"""
    if session_manager.delete_session(session_id):
        logger.info(f"Deleted session {session_id}")
        return {"status": "deleted"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.get("/test-types", response_model=Dict[str, list])
async def get_test_types() -> Dict[str, list]:
    """Get available test types"""
    return {"test_types": [t.name for t in TestType if t != TestType.NULL]}
