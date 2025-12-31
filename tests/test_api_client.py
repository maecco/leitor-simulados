"""
Tests for the desktop client API client
"""
import pytest
import responses
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add desktop_client to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "desktop_client"))
sys.path.insert(0, str(PROJECT_ROOT))

from desktop_client.api_client import APIClient, APIError


@pytest.fixture
def client():
    """Create an API client"""
    return APIClient(base_url="http://localhost:8000")


class TestAPIClientInit:
    """Tests for API client initialization"""
    
    def test_default_base_url(self):
        """Test default base URL"""
        client = APIClient()
        assert client.base_url == "http://localhost:8000"
    
    def test_custom_base_url(self):
        """Test custom base URL"""
        client = APIClient(base_url="http://custom:9000")
        assert client.base_url == "http://custom:9000"
    
    def test_url_building(self, client):
        """Test URL building"""
        assert client._url("/api/test") == "http://localhost:8000/api/test"
    
    def test_url_building_trailing_slash(self):
        """Test URL building with trailing slash"""
        client = APIClient(base_url="http://localhost:8000/")
        assert client._url("/api/test") == "http://localhost:8000/api/test"


class TestAPIClientSessions:
    """Tests for session-related API calls"""
    
    @responses.activate
    def test_create_session(self, client):
        """Test creating a session"""
        responses.add(
            responses.POST,
            "http://localhost:8000/api/session/create",
            json={"session_id": "test-123", "test_type": "SIMUFSC"},
            status=200
        )
        
        result = client.create_session("SIMUFSC")
        
        assert result["session_id"] == "test-123"
        assert result["test_type"] == "SIMUFSC"
    
    @responses.activate
    def test_create_session_error(self, client):
        """Test creating a session with error"""
        responses.add(
            responses.POST,
            "http://localhost:8000/api/session/create",
            json={"detail": "Invalid test type"},
            status=400
        )
        
        with pytest.raises(APIError) as exc_info:
            client.create_session("INVALID")
        
        assert "400" in str(exc_info.value)
    
    @responses.activate
    def test_get_session(self, client):
        """Test getting a session"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/session/test-123",
            json={
                "session_id": "test-123",
                "test_type": "SIMUFSC",
                "image_count": 5,
                "processed_count": 3
            },
            status=200
        )
        
        result = client.get_session("test-123")
        
        assert result["session_id"] == "test-123"
        assert result["image_count"] == 5
    
    @responses.activate
    def test_delete_session(self, client):
        """Test deleting a session"""
        responses.add(
            responses.DELETE,
            "http://localhost:8000/api/session/test-123",
            json={"status": "deleted"},
            status=200
        )
        
        result = client.delete_session("test-123")
        
        assert result["status"] == "deleted"


class TestAPIClientModels:
    """Tests for model-related API calls"""
    
    @responses.activate
    def test_get_models(self, client):
        """Test getting available models"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/models",
            json={
                "models": [
                    {"name": "model1", "model_type": "YOLOV8", "target_stage": "FIRST"},
                    {"name": "model2", "model_type": "YOLOV8", "target_stage": "SECOND"}
                ]
            },
            status=200
        )
        
        result = client.get_models()
        
        assert len(result) == 2
        assert result[0]["name"] == "model1"


class TestAPIClientImages:
    """Tests for image-related API calls"""
    
    @responses.activate
    def test_get_images(self, client):
        """Test getting images list"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/images/test-123",
            json={
                "images": [
                    {"id": "img1", "filename": "test1.jpg", "processed": False},
                    {"id": "img2", "filename": "test2.jpg", "processed": True}
                ]
            },
            status=200
        )
        
        result = client.get_images("test-123")
        
        assert len(result["images"]) == 2
    
    @responses.activate
    def test_get_image(self, client):
        """Test getting a single image"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/image/test-123/img1",
            json={
                "id": "img1",
                "filename": "test.jpg",
                "image": "base64data==",
                "processed": False
            },
            status=200
        )
        
        result = client.get_image("test-123", "img1")
        
        assert result["id"] == "img1"
        assert "image" in result
    
    def test_upload_images(self, client, temp_image_files):
        """Test uploading images (mocked)"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "uploaded": [{"id": "img1", "filename": "test.jpg"}],
                "total": 1
            }
            mock_post.return_value = mock_response
            
            result = client.upload_images("test-123", [str(temp_image_files[0])])
            
            assert result["total"] == 1


class TestAPIClientProcessing:
    """Tests for processing-related API calls"""
    
    @responses.activate
    def test_process_image(self, client):
        """Test processing an image"""
        responses.add(
            responses.POST,
            "http://localhost:8000/api/process/test-123/img1",
            json={
                "status": "success",
                "image_id": "img1",
                "detections_count": 45,
                "report": {
                    "owner_cpf": "12345678901",
                    "questions": [{"number": 1, "answer": "A", "updated": False}],
                    "test_type": "SIMUFSC"
                }
            },
            status=200
        )
        
        result = client.process_image(
            "test-123", "img1",
            fs_model="model1.pt",
            ss_model="model2.pt"
        )
        
        assert result["status"] == "success"
        assert result["detections_count"] == 45
        assert result["report"] is not None
    
    @responses.activate
    def test_process_all_images(self, client):
        """Test processing all images"""
        responses.add(
            responses.POST,
            "http://localhost:8000/api/process-all/test-123",
            json={
                "results": [
                    {"image_id": "img1", "status": "success", "detections_count": 45},
                    {"image_id": "img2", "status": "success", "detections_count": 42}
                ]
            },
            status=200
        )
        
        result = client.process_all_images(
            "test-123",
            fs_model="model1.pt",
            ss_model="model2.pt"
        )
        
        assert len(result["results"]) == 2


class TestAPIClientReports:
    """Tests for report-related API calls"""
    
    @responses.activate
    def test_get_report(self, client):
        """Test getting a report"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/report/test-123/img1",
            json={
                "report": {
                    "owner_cpf": "12345678901",
                    "questions": [
                        {"number": 1, "answer": "A", "updated": False},
                        {"number": 2, "answer": "B", "updated": False}
                    ],
                    "test_type": "SIMUFSC"
                }
            },
            status=200
        )
        
        result = client.get_report("test-123", "img1")
        
        assert result["report"]["owner_cpf"] == "12345678901"
        assert len(result["report"]["questions"]) == 2
    
    @responses.activate
    def test_get_all_reports(self, client):
        """Test getting all reports"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/reports/test-123",
            json={
                "reports": [
                    {"image_id": "img1", "filename": "test1.jpg", "report": {}},
                    {"image_id": "img2", "filename": "test2.jpg", "report": {}}
                ]
            },
            status=200
        )
        
        result = client.get_all_reports("test-123")
        
        assert len(result["reports"]) == 2
    
    @responses.activate
    def test_update_answer(self, client):
        """Test updating an answer"""
        responses.add(
            responses.POST,
            "http://localhost:8000/api/update-answer/test-123/img1",
            json={
                "status": "updated",
                "question": 5,
                "answer": "C"
            },
            status=200
        )
        
        result = client.update_answer("test-123", "img1", 5, "C")
        
        assert result["status"] == "updated"
        assert result["question"] == 5
        assert result["answer"] == "C"


class TestAPIClientExport:
    """Tests for export-related API calls"""
    
    @responses.activate
    def test_export_json(self, client):
        """Test exporting as JSON"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/export/test-123",
            json={"reports": []},
            status=200
        )
        
        result = client.export_reports("test-123", "json")
        
        assert "reports" in result
    
    @responses.activate
    def test_export_csv(self, client):
        """Test exporting as CSV"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/export/test-123",
            json={"csv": "filename,cpf\ntest.jpg,123"},
            status=200
        )
        
        result = client.export_reports("test-123", "csv")
        
        assert "csv" in result


class TestAPIError:
    """Tests for API error handling"""
    
    @responses.activate
    def test_server_error(self, client):
        """Test handling server errors"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/session/test",
            json={"detail": "Internal server error"},
            status=500
        )
        
        with pytest.raises(APIError) as exc_info:
            client.get_session("test")
        
        assert "500" in str(exc_info.value)
    
    @responses.activate
    def test_not_found_error(self, client):
        """Test handling not found errors"""
        responses.add(
            responses.GET,
            "http://localhost:8000/api/session/nonexistent",
            json={"detail": "Session not found"},
            status=404
        )
        
        with pytest.raises(APIError) as exc_info:
            client.get_session("nonexistent")
        
        assert "404" in str(exc_info.value)
        assert "Session not found" in str(exc_info.value)
