"""
Jobs Router
Handles background job status and management endpoints
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, status

from dependencies import JobManagerDep
from services.job_manager import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/", response_model=Dict[str, Any])
async def get_job_stats(
    job_manager: JobManagerDep
) -> Dict[str, Any]:
    """Get job manager statistics"""
    return job_manager.get_stats()


@router.get("/session/{session_id}", response_model=Dict[str, List[Dict[str, Any]]])
async def get_session_jobs(
    session_id: str,
    job_manager: JobManagerDep
) -> Dict[str, List[Dict[str, Any]]]:
    """Get all jobs for a session"""
    jobs = job_manager.get_jobs_for_session(session_id)
    return {
        "jobs": [job.to_dict() for job in jobs]
    }


@router.get("/{job_id}", response_model=Dict[str, Any])
async def get_job_status(
    job_id: str,
    job_manager: JobManagerDep
) -> Dict[str, Any]:
    """
    Get the status and progress of a background job.
    
    Poll this endpoint to track progress of batch processing.
    Recommended polling interval: 1-3 seconds.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    response = job.to_dict()
    
    # Include results only if job is completed
    if job.status == JobStatus.COMPLETED:
        response["results"] = job.results
    
    return response


@router.get("/{job_id}/results", response_model=Dict[str, Any])
async def get_job_results(
    job_id: str,
    job_manager: JobManagerDep
) -> Dict[str, Any]:
    """
    Get the full results of a completed job.
    
    Only available after job status is 'completed'.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status.value}"
        )
    
    return {
        "job_id": job_id,
        "results": job.results,
        "summary": {
            "total": job.progress.total,
            "successful": job.progress.successful,
            "failed": job.progress.failed
        }
    }


@router.post("/{job_id}/cancel", response_model=Dict[str, Any])
async def cancel_job(
    job_id: str,
    job_manager: JobManagerDep
) -> Dict[str, Any]:
    """
    Cancel a pending or running job.
    
    Note: Already processing images will complete, but no new images
    will be processed after cancellation.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status.value}"
        )
    
    job_manager.cancel_job(job_id)
    
    return {
        "status": "cancelled",
        "job_id": job_id,
        "message": "Job cancellation requested"
    }


@router.delete("/{job_id}", response_model=Dict[str, Any])
async def delete_job(
    job_id: str,
    job_manager: JobManagerDep
) -> Dict[str, Any]:
    """
    Delete a completed, failed, or cancelled job.
    
    Running jobs cannot be deleted - cancel them first.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if not job_manager.delete_job(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete job with status: {job.status.value}"
        )
    
    return {
        "status": "deleted",
        "job_id": job_id
    }
