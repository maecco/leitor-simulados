"""
Processing Router
Handles image processing with ML models
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Form, status

from dependencies import (
    SessionManagerDep,
    ProcessingServiceDep,
    JobManagerDep,
    ValidSessionDep,
    ValidImageDep,
)
from services.job_manager import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["processing"])


@router.get("/models", response_model=Dict[str, List[Dict[str, Any]]])
async def get_models(
    processing_service: ProcessingServiceDep
) -> Dict[str, List[Dict[str, Any]]]:
    """Get available detection models"""
    return {"models": processing_service.get_available_models()}


@router.post("/process/{session_id}/{image_id}", response_model=Dict[str, Any])
async def process_image(
    session_id: str,
    image_id: str,
    session: ValidSessionDep,
    image_data: ValidImageDep,
    session_manager: SessionManagerDep,
    processing_service: ProcessingServiceDep,
    fs_model: str = Form(...),
    ss_model: str = Form(...),
    fs_threshold: float = Form(0.5),
    ss_threshold: float = Form(0.5)
) -> Dict[str, Any]:
    """Process a single image with detection models"""
    try:
        logger.info(f"Processing image {image_id} in session {session_id}")
        
        result = processing_service.process_image(
            image_data["raw"],
            image_data["filename"],
            session.test_type,
            fs_model,
            ss_model,
            fs_threshold,
            ss_threshold
        )
        
        # Update session with results
        session_manager.update_image_results(
            session_id, image_id,
            processed_image=result["processed_image"],
            detections=result["detections"],
            blocks=result["blocks"],
            report=result["report"]
        )
        
        logger.info(f"Successfully processed image {image_id}: {len(result['detections'])} detections")
        
        return {
            "status": "success",
            "image_id": image_id,
            "detections_count": len(result["detections"]),
            "report": result["report"].to_dict() if result["report"] else None
        }
        
    except Exception as e:
        logger.error(f"Error processing image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/process-all/{session_id}", response_model=Dict[str, Any])
async def process_all_images(
    session_id: str,
    session: ValidSessionDep,
    session_manager: SessionManagerDep,
    processing_service: ProcessingServiceDep,
    job_manager: JobManagerDep,
    fs_model: str = Form(...),
    ss_model: str = Form(...),
    fs_threshold: float = Form(0.5),
    ss_threshold: float = Form(0.5)
) -> Dict[str, Any]:
    """
    Process all images in a session as a background job.
    
    Returns immediately with a job_id. Use GET /api/jobs/{job_id} to 
    poll for progress and results.
    
    Recommended polling interval: 1-3 seconds.
    """
    if not session.images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No images in session to process"
        )
    
    # Create background job
    job = job_manager.create_job(session_id, len(session.images))
    
    logger.info(
        f"Starting background job {job.job_id} for session {session_id} "
        f"({len(session.images)} images)"
    )
    
    # Define the background task function
    def process_batch_task(
        job_id: str,
        images: Dict[str, Dict[str, Any]],
        test_type,
        fs_model_path: str,
        ss_model_path: str,
        fs_thresh: float,
        ss_thresh: float
    ):
        """Background task to process all images"""
        success_count = 0
        error_count = 0
        
        for idx, (image_id, img_data) in enumerate(images.items()):
            # Check if job was cancelled
            if job_manager.is_job_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled at image {idx + 1}")
                break
            
            try:
                result = processing_service.process_image(
                    img_data["raw"],
                    img_data["filename"],
                    test_type,
                    fs_model_path,
                    ss_model_path,
                    fs_thresh,
                    ss_thresh
                )
                
                # Update session with results
                session_manager.update_image_results(
                    session_id, image_id,
                    processed_image=result["processed_image"],
                    detections=result["detections"],
                    blocks=result["blocks"],
                    report=result["report"]
                )
                
                success_count += 1
                job_manager.add_result(job_id, {
                    "image_id": image_id,
                    "filename": img_data["filename"],
                    "status": "success",
                    "detections_count": len(result["detections"])
                })
                
            except Exception as e:
                logger.error(f"Error processing image {image_id} in job {job_id}: {e}")
                error_count += 1
                job_manager.add_result(job_id, {
                    "image_id": image_id,
                    "filename": img_data["filename"],
                    "status": "error",
                    "error": str(e)
                })
            
            # Update progress
            job_manager.update_progress(
                job_id,
                processed=idx + 1,
                successful=success_count,
                failed=error_count
            )
    
    # Submit job for background execution
    job_manager.submit_job(
        job.job_id,
        process_batch_task,
        dict(session.images),  # Copy to avoid threading issues
        session.test_type,
        fs_model,
        ss_model,
        fs_threshold,
        ss_threshold
    )
    
    return {
        "status": "accepted",
        "job_id": job.job_id,
        "message": f"Processing {len(session.images)} images in background",
        "poll_url": f"/api/jobs/{job.job_id}",
        "total_images": len(session.images)
    }
