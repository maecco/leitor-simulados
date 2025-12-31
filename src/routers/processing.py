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
    ValidSessionDep,
    ValidImageDep,
)

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
    fs_model: str = Form(...),
    ss_model: str = Form(...),
    fs_threshold: float = Form(0.5),
    ss_threshold: float = Form(0.5)
) -> Dict[str, Any]:
    """Process all images in a session"""
    results = []
    success_count = 0
    error_count = 0
    
    logger.info(f"Processing all {len(session.images)} images in session {session_id}")
    
    for image_id, img_data in session.images.items():
        try:
            result = processing_service.process_image(
                img_data["raw"],
                img_data["filename"],
                session.test_type,
                fs_model,
                ss_model,
                fs_threshold,
                ss_threshold
            )
            
            session_manager.update_image_results(
                session_id, image_id,
                processed_image=result["processed_image"],
                detections=result["detections"],
                blocks=result["blocks"],
                report=result["report"]
            )
            
            results.append({
                "image_id": image_id,
                "filename": img_data["filename"],
                "status": "success",
                "detections_count": len(result["detections"])
            })
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error processing image {image_id}: {e}")
            results.append({
                "image_id": image_id,
                "filename": img_data["filename"],
                "status": "error",
                "error": str(e)
            })
            error_count += 1
    
    logger.info(f"Batch processing complete: {success_count} success, {error_count} errors")
    
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "success": success_count,
            "errors": error_count
        }
    }
