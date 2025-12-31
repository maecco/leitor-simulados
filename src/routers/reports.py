"""
Reports Router
Handles report retrieval, updates, and exports
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Form, status
from fastapi.responses import JSONResponse

from dependencies import (
    ProcessingServiceDep,
    ValidSessionDep,
    ValidImageDep,
    ValidReportDep,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/report/{session_id}/{image_id}", response_model=Dict[str, Any])
async def get_report(
    image_id: str,
    report: ValidReportDep
) -> Dict[str, Any]:
    """Get the report for a processed image"""
    return {"report": report.to_dict()}


@router.get("/reports/{session_id}", response_model=Dict[str, Any])
async def get_all_reports(session: ValidSessionDep) -> Dict[str, Any]:
    """Get all reports for a session"""
    reports = []
    for img_id, img_data in session.images.items():
        report = img_data.get("report")
        if report:
            reports.append({
                "image_id": img_id,
                "filename": img_data["filename"],
                "report": report.to_dict()
            })
    
    return {
        "reports": reports,
        "total": len(reports)
    }


@router.post("/update-answer/{session_id}/{image_id}", response_model=Dict[str, Any])
async def update_answer(
    image_id: str,
    report: ValidReportDep,
    question_number: int = Form(...),
    answer: str = Form(...)
) -> Dict[str, Any]:
    """Manually update an answer in the report"""
    try:
        report.update_answer(question_number, answer)
        logger.info(f"Updated answer for question {question_number} in image {image_id}")
        
        return {
            "status": "updated",
            "question": question_number,
            "answer": answer
        }
    except Exception as e:
        logger.error(f"Error updating answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/export/{session_id}", response_model=None)
async def export_reports(
    session: ValidSessionDep,
    processing_service: ProcessingServiceDep,
    format: str = "json"
) -> JSONResponse:
    """Export all reports in the specified format"""
    reports = []
    for img_id, img_data in session.images.items():
        report = img_data.get("report")
        if report:
            reports.append({
                "filename": img_data["filename"],
                "report": report.to_dict()
            })
    
    if format == "json":
        return JSONResponse(content={
            "reports": reports,
            "total": len(reports)
        })
    
    elif format == "csv":
        csv_content = processing_service.export_to_csv(reports)
        return JSONResponse(content={
            "csv": csv_content,
            "total": len(reports)
        })
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {format}. Supported formats: json, csv"
        )
