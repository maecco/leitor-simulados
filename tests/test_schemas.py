"""
Tests for Pydantic schemas
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.schemas import (
    ModelInfo,
    SessionInfo,
    ImageInfo,
    ProcessingRequest,
    ProcessingResponse,
    QuestionAnswer,
    ReportResponse,
    TestTypeEnum,
    StageEnum
)


class TestEnums:
    """Tests for enum schemas"""
    
    def test_test_type_enum_values(self):
        """Test TestTypeEnum has correct values"""
        assert TestTypeEnum.PS_ALUNOS == "PS_ALUNOS"
        assert TestTypeEnum.SIMUFSC == "SIMUFSC"
        assert TestTypeEnum.SIMUENEM == "SIMUENEM"
    
    def test_stage_enum_values(self):
        """Test StageEnum has correct values"""
        assert StageEnum.FIRST == "FIRST"
        assert StageEnum.SECOND == "SECOND"
        assert StageEnum.BOTH == "BOTH"


class TestModelInfo:
    """Tests for ModelInfo schema"""
    
    def test_model_info_creation(self):
        """Test creating ModelInfo"""
        model = ModelInfo(
            name="test_model",
            model_type="YOLOV8",
            target_stage="FIRST",
            rel_path="YoloV8/first_stage/test.pt"
        )
        
        assert model.name == "test_model"
        assert model.model_type == "YOLOV8"
        assert model.target_stage == "FIRST"
        assert model.rel_path == "YoloV8/first_stage/test.pt"
    
    def test_model_info_dict(self):
        """Test ModelInfo to dict conversion"""
        model = ModelInfo(
            name="test_model",
            model_type="YOLOV8",
            target_stage="FIRST",
            rel_path="path/to/model.pt"
        )
        
        data = model.model_dump()
        assert data["name"] == "test_model"


class TestSessionInfo:
    """Tests for SessionInfo schema"""
    
    def test_session_info_creation(self):
        """Test creating SessionInfo"""
        session = SessionInfo(
            session_id="test-123",
            test_type="SIMUFSC",
            image_count=5,
            processed_count=3
        )
        
        assert session.session_id == "test-123"
        assert session.test_type == "SIMUFSC"
        assert session.image_count == 5
        assert session.processed_count == 3


class TestImageInfo:
    """Tests for ImageInfo schema"""
    
    def test_image_info_creation(self):
        """Test creating ImageInfo"""
        image = ImageInfo(
            id="img-123",
            filename="test.jpg",
            processed=True,
            has_report=True
        )
        
        assert image.id == "img-123"
        assert image.filename == "test.jpg"
        assert image.processed is True
        assert image.has_report is True


class TestProcessingRequest:
    """Tests for ProcessingRequest schema"""
    
    def test_processing_request_defaults(self):
        """Test ProcessingRequest default values"""
        request = ProcessingRequest(
            fs_model="model1.pt",
            ss_model="model2.pt"
        )
        
        assert request.fs_threshold == 0.5
        assert request.ss_threshold == 0.5
    
    def test_processing_request_custom(self):
        """Test ProcessingRequest with custom values"""
        request = ProcessingRequest(
            fs_model="model1.pt",
            ss_model="model2.pt",
            fs_threshold=0.7,
            ss_threshold=0.3
        )
        
        assert request.fs_threshold == 0.7
        assert request.ss_threshold == 0.3


class TestQuestionAnswer:
    """Tests for QuestionAnswer schema"""
    
    def test_question_answer_creation(self):
        """Test creating QuestionAnswer"""
        qa = QuestionAnswer(
            number=1,
            answer="A"
        )
        
        assert qa.number == 1
        assert qa.answer == "A"
        assert qa.updated is False
    
    def test_question_answer_updated(self):
        """Test QuestionAnswer with updated flag"""
        qa = QuestionAnswer(
            number=1,
            answer="B",
            updated=True
        )
        
        assert qa.updated is True


class TestReportResponse:
    """Tests for ReportResponse schema"""
    
    def test_report_response_creation(self):
        """Test creating ReportResponse"""
        report = ReportResponse(
            owner_cpf="12345678901",
            questions=[
                QuestionAnswer(number=1, answer="A"),
                QuestionAnswer(number=2, answer="B")
            ],
            test_type="SIMUFSC"
        )
        
        assert report.owner_cpf == "12345678901"
        assert len(report.questions) == 2
        assert report.test_type == "SIMUFSC"


class TestProcessingResponse:
    """Tests for ProcessingResponse schema"""
    
    def test_processing_response_without_report(self):
        """Test ProcessingResponse without report"""
        response = ProcessingResponse(
            status="success",
            image_id="img-123",
            detections_count=45
        )
        
        assert response.status == "success"
        assert response.image_id == "img-123"
        assert response.detections_count == 45
        assert response.report is None
    
    def test_processing_response_with_report(self):
        """Test ProcessingResponse with report"""
        report = ReportResponse(
            owner_cpf="12345678901",
            questions=[QuestionAnswer(number=1, answer="A")],
            test_type="SIMUFSC"
        )
        
        response = ProcessingResponse(
            status="success",
            image_id="img-123",
            detections_count=45,
            report=report
        )
        
        assert response.report is not None
        assert response.report.owner_cpf == "12345678901"
