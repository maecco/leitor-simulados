"""
Pydantic schemas for API request/response validation
"""
from typing import Optional, Any
from pydantic import BaseModel
from enum import Enum


class TestTypeEnum(str, Enum):
    PS_ALUNOS = "PS_ALUNOS"
    SIMULINHO = "SIMULINHO"
    SIMUFSC = "SIMUFSC"
    SIMUENEM = "SIMUENEM"


class StageEnum(str, Enum):
    FIRST = "FIRST"
    SECOND = "SECOND"
    BOTH = "BOTH"


class ModelInfo(BaseModel):
    name: str
    model_type: str
    target_stage: str
    rel_path: str


class SessionInfo(BaseModel):
    session_id: str
    test_type: str
    image_count: int
    processed_count: int


class ImageInfo(BaseModel):
    id: str
    filename: str
    processed: bool
    has_report: bool


class ProcessingRequest(BaseModel):
    fs_model: str
    ss_model: str
    fs_threshold: float = 0.5
    ss_threshold: float = 0.5


class DetectionInfo(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: dict


class QuestionAnswer(BaseModel):
    number: int
    answer: str
    updated: bool = False


class ReportResponse(BaseModel):
    owner_cpf: str
    questions: list[QuestionAnswer]
    test_type: str


class ProcessingResponse(BaseModel):
    status: str
    image_id: str
    detections_count: int
    report: Optional[ReportResponse] = None


class ExportRequest(BaseModel):
    format: str = "json"  # json, csv, excel


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
