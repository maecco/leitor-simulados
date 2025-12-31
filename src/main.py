"""
FastAPI Web Application for Leitor de Simulados
Handles image processing, detection, and report generation
"""
import sys
from pathlib import Path

# Add the project root to the path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import uuid
import base64
from io import BytesIO
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import cv2
import numpy as np

from core.definitions.enums import TestType, Stage
from core.definitions.question import TestReport
from core.image import CoreImage
from core.model import DetectionModel
from core.detection import Detection
from core.builder import Builder
from core.definitions.blocks import TestBlocks
from core.IO.base import Importer

from services.session_manager import SessionManager
from services.processing import ProcessingService
from schemas import (
    ProcessingRequest,
    ProcessingResponse,
    SessionInfo,
    ModelInfo,
    ReportResponse,
    ImageInfo
)

# Initialize FastAPI app
app = FastAPI(
    title="Leitor de Simulados API",
    description="REST API for processing exam answer sheets with YOLO detection models",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
session_manager = SessionManager()
processing_service = ProcessingService()


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """API root - redirect to docs"""
    return {
        "message": "Leitor de Simulados API",
        "docs": "/docs",
        "version": "2.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/test-types")
async def get_test_types():
    """Get available test types"""
    return {"test_types": [t.name for t in TestType if t != TestType.NULL]}


@app.post("/api/session/create")
async def create_session(test_type: str = Form(...)):
    """Create a new processing session"""
    try:
        test_type_enum = TestType[test_type]
        session_id = session_manager.create_session(test_type_enum)
        return {"session_id": session_id, "test_type": test_type}
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid test type: {test_type}")


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and cleanup resources"""
    if session_manager.delete_session(session_id):
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/models")
async def get_models():
    """Get available detection models"""
    return {"models": processing_service.get_available_models()}


@app.post("/api/upload/{session_id}")
async def upload_images(
    session_id: str,
    files: list[UploadFile] = File(...)
):
    """Upload images to a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    uploaded = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        
        contents = await file.read()
        image_id = session_manager.add_image(session_id, file.filename, contents)
        if image_id:
            uploaded.append({"id": image_id, "filename": file.filename})
    
    return {"uploaded": uploaded, "total": len(uploaded)}


@app.get("/api/images/{session_id}")
async def get_images(session_id: str):
    """Get list of images in a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    images = []
    for img_id, img_data in session.images.items():
        images.append({
            "id": img_id,
            "filename": img_data["filename"],
            "processed": img_data.get("processed", False),
            "has_report": img_data.get("report") is not None
        })
    return {"images": images}


@app.get("/api/image/{session_id}/{image_id}")
async def get_image(session_id: str, image_id: str, with_detections: bool = False):
    """Get a specific image (optionally with detection boxes drawn)"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    img_data = session.images.get(image_id)
    if not img_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Get the image (with or without detections)
    if with_detections and img_data.get("processed_image") is not None:
        img_bytes = img_data["processed_image"]
    else:
        img_bytes = img_data["raw"]
    
    # Convert to base64 for JSON response
    b64_image = base64.b64encode(img_bytes).decode("utf-8")
    
    return {
        "id": image_id,
        "filename": img_data["filename"],
        "image": b64_image,
        "processed": img_data.get("processed", False)
    }


@app.post("/api/process/{session_id}/{image_id}")
async def process_image(
    session_id: str,
    image_id: str,
    fs_model: str = Form(...),
    ss_model: str = Form(...),
    fs_threshold: float = Form(0.5),
    ss_threshold: float = Form(0.5)
):
    """Process a single image with detection models"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    img_data = session.images.get(image_id)
    if not img_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
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
        
        # Update session with results
        session_manager.update_image_results(
            session_id, image_id,
            processed_image=result["processed_image"],
            detections=result["detections"],
            blocks=result["blocks"],
            report=result["report"]
        )
        
        return {
            "status": "success",
            "image_id": image_id,
            "detections_count": len(result["detections"]),
            "report": result["report"].to_dict() if result["report"] else None
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-all/{session_id}")
async def process_all_images(
    session_id: str,
    fs_model: str = Form(...),
    ss_model: str = Form(...),
    fs_threshold: float = Form(0.5),
    ss_threshold: float = Form(0.5)
):
    """Process all images in a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    results = []
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
                "status": "success",
                "detections_count": len(result["detections"])
            })
        except Exception as e:
            results.append({
                "image_id": image_id,
                "status": "error",
                "error": str(e)
            })
    
    return {"results": results}


@app.get("/api/report/{session_id}/{image_id}")
async def get_report(session_id: str, image_id: str):
    """Get the report for a processed image"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    img_data = session.images.get(image_id)
    if not img_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
    report = img_data.get("report")
    if not report:
        raise HTTPException(status_code=404, detail="Report not found. Process the image first.")
    
    return {"report": report.to_dict()}


@app.get("/api/reports/{session_id}")
async def get_all_reports(session_id: str):
    """Get all reports for a session"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    reports = []
    for img_id, img_data in session.images.items():
        report = img_data.get("report")
        if report:
            reports.append({
                "image_id": img_id,
                "filename": img_data["filename"],
                "report": report.to_dict()
            })
    
    return {"reports": reports}


@app.post("/api/update-answer/{session_id}/{image_id}")
async def update_answer(
    session_id: str,
    image_id: str,
    question_number: int = Form(...),
    answer: str = Form(...)
):
    """Manually update an answer in the report"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    img_data = session.images.get(image_id)
    if not img_data:
        raise HTTPException(status_code=404, detail="Image not found")
    
    report = img_data.get("report")
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        # Update the answer in the report
        report.update_answer(question_number, answer)
        return {"status": "updated", "question": question_number, "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/export/{session_id}")
async def export_reports(session_id: str, format: str = "json"):
    """Export all reports in the specified format"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    reports = []
    for img_id, img_data in session.images.items():
        report = img_data.get("report")
        if report:
            reports.append({
                "filename": img_data["filename"],
                "report": report.to_dict()
            })
    
    if format == "json":
        return JSONResponse(content={"reports": reports})
    elif format == "csv":
        # Generate CSV content
        csv_content = processing_service.export_to_csv(reports)
        return JSONResponse(content={"csv": csv_content})
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


# =============================================================================
# WebSocket for real-time processing updates
# =============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time processing updates"""
    await websocket.accept()
    
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "process":
                # Process images and send updates
                for image_id in data.get("image_ids", []):
                    await websocket.send_json({
                        "type": "processing",
                        "image_id": image_id,
                        "status": "started"
                    })
                    
                    # Process the image
                    # ... (processing logic)
                    
                    await websocket.send_json({
                        "type": "processing",
                        "image_id": image_id,
                        "status": "completed"
                    })
    except WebSocketDisconnect:
        pass


# =============================================================================
# Application startup/shutdown
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    print("🚀 Leitor de Simulados Web Server Starting...")
    processing_service.initialize()
    print("✅ Models loaded successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown"""
    print("🛑 Shutting down...")
    session_manager.cleanup_all()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
