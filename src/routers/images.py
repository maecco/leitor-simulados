"""
Images Router
Handles image upload and retrieval
"""
import logging
import base64
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, UploadFile, File, status

from dependencies import (
    SessionManagerDep,
    ValidSessionDep,
    ValidImageDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["images"])


@router.post("/upload/{session_id}", response_model=Dict[str, Any])
async def upload_images(
    session_id: str,
    session: ValidSessionDep,
    session_manager: SessionManagerDep,
    files: List[UploadFile] = File(...)
) -> Dict[str, Any]:
    """Upload images to a session"""
    uploaded = []
    skipped = []
    
    for file in files:
        if not file.content_type or not file.content_type.startswith("image/"):
            skipped.append({"filename": file.filename, "reason": "Not an image"})
            continue
        
        contents = await file.read()
        image_id = session_manager.add_image(session_id, file.filename, contents)
        
        if image_id:
            uploaded.append({"id": image_id, "filename": file.filename})
            logger.debug(f"Uploaded image {file.filename} to session {session_id}")
    
    logger.info(f"Uploaded {len(uploaded)} images to session {session_id}")
    
    return {
        "uploaded": uploaded,
        "skipped": skipped,
        "total": len(uploaded)
    }


@router.get("/images/{session_id}", response_model=Dict[str, Any])
async def get_images(session: ValidSessionDep) -> Dict[str, Any]:
    """Get list of images in a session"""
    images = []
    for img_id, img_data in session.images.items():
        images.append({
            "id": img_id,
            "filename": img_data["filename"],
            "processed": img_data.get("processed", False),
            "has_report": img_data.get("report") is not None
        })
    
    return {"images": images, "total": len(images)}


@router.get("/image/{session_id}/{image_id}", response_model=Dict[str, Any])
async def get_image(
    image_id: str,
    image_data: ValidImageDep,
    with_detections: bool = False
) -> Dict[str, Any]:
    """Get a specific image (optionally with detection boxes drawn)"""
    # Get the image (with or without detections)
    if with_detections and image_data.get("processed_image") is not None:
        img_bytes = image_data["processed_image"]
    else:
        img_bytes = image_data["raw"]
    
    # Convert to base64 for JSON response
    b64_image = base64.b64encode(img_bytes).decode("utf-8")
    
    return {
        "id": image_id,
        "filename": image_data["filename"],
        "image": b64_image,
        "processed": image_data.get("processed", False)
    }


@router.delete("/image/{session_id}/{image_id}", response_model=Dict[str, str])
async def delete_image(
    session_id: str,
    image_id: str,
    session: ValidSessionDep,
    session_manager: SessionManagerDep
) -> Dict[str, str]:
    """Delete an image from a session"""
    if session_manager.delete_image(session_id, image_id):
        logger.info(f"Deleted image {image_id} from session {session_id}")
        return {"status": "deleted"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Image not found"
    )
