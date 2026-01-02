"""
FastAPI Dependencies
Provides dependency injection for services and common validations
"""
from typing import Annotated
from functools import lru_cache

from fastapi import Depends, HTTPException, status

from services.session_manager import SessionManager, Session
from services.processing import ProcessingService
from services.job_manager import JobManager
from config import Settings, get_settings


# =============================================================================
# Service Dependencies (Singletons)
# =============================================================================

@lru_cache()
def get_session_manager() -> SessionManager:
    """Get singleton SessionManager instance"""
    return SessionManager()


@lru_cache()
def get_processing_service() -> ProcessingService:
    """Get singleton ProcessingService instance"""
    service = ProcessingService()
    service.initialize()
    return service


@lru_cache()
def get_job_manager() -> JobManager:
    """Get singleton JobManager instance"""
    # Set use_parallel=True for parallel image processing (higher memory)
    return JobManager(use_parallel=False)


# Type aliases for cleaner dependency injection
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
ProcessingServiceDep = Annotated[ProcessingService, Depends(get_processing_service)]
JobManagerDep = Annotated[JobManager, Depends(get_job_manager)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


# =============================================================================
# Validation Dependencies
# =============================================================================

def get_valid_session(
    session_id: str,
    session_manager: SessionManagerDep
) -> Session:
    """
    Dependency that validates session exists and returns it.
    Raises HTTPException 404 if session not found.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    return session


# Type alias for validated session
ValidSessionDep = Annotated[Session, Depends(get_valid_session)]


def get_valid_image(
    image_id: str,
    session: ValidSessionDep
) -> dict:
    """
    Dependency that validates image exists in session and returns it.
    Raises HTTPException 404 if image not found.
    """
    img_data = session.images.get(image_id)
    if not img_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    return img_data


# Type alias for validated image
ValidImageDep = Annotated[dict, Depends(get_valid_image)]


def get_valid_report(image_data: ValidImageDep) -> object:
    """
    Dependency that validates report exists for image.
    Raises HTTPException 404 if report not found.
    """
    report = image_data.get("report")
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. Process the image first."
        )
    return report


ValidReportDep = Annotated[object, Depends(get_valid_report)]
