"""
Tests for the FastAPI src endpoints
"""
import pytest
import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Skip all tests if core dependencies are missing
try:
    from fastapi.testclient import TestClient
    from src.main import app
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    SKIP_REASON = f"Core dependencies not available: {e}"


pytestmark = pytest.mark.skipif(not DEPS_AVAILABLE, reason="Core dependencies not available")


@pytest.fixture
def client():
    """Create a test client"""
    if not DEPS_AVAILABLE:
        pytest.skip(SKIP_REASON)
    return TestClient(app)


@pytest.fixture
def session_id(client):
    """Create a session and return its ID"""
    response = client.post("/api/session/create", data={"test_type": "SIMUFSC"})
    return response.json()["session_id"]


class TestSessionEndpoints:
    """Tests for session management endpoints"""
    
    def test_create_session(self, client):
        """Test creating a new session"""
        response = client.post(
            "/api/session/create",
            data={"test_type": "SIMUFSC"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["test_type"] == "SIMUFSC"
    
    def test_create_session_invalid_type(self, client):
        """Test creating a session with invalid test type"""
        response = client.post(
            "/api/session/create",
            data={"test_type": "INVALID_TYPE"}
        )
        
        assert response.status_code == 400
    
    def test_get_session(self, client, session_id):
        """Test retrieving session info"""
        response = client.get(f"/api/session/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["test_type"] == "SIMUFSC"
    
    def test_get_nonexistent_session(self, client):
        """Test retrieving a nonexistent session"""
        response = client.get("/api/session/nonexistent-id")
        
        assert response.status_code == 404
    
    def test_delete_session(self, client, session_id):
        """Test deleting a session"""
        response = client.delete(f"/api/session/{session_id}")
        
        assert response.status_code == 200
        
        # Verify it's gone
        response = client.get(f"/api/session/{session_id}")
        assert response.status_code == 404


class TestModelsEndpoint:
    """Tests for the models endpoint"""
    
    def test_get_models(self, client):
        """Test getting available models"""
        response = client.get("/api/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)


class TestImageEndpoints:
    """Tests for image management endpoints"""
    
    def test_upload_image(self, client, session_id, sample_image_bytes):
        """Test uploading an image"""
        response = client.post(
            f"/api/upload/{session_id}",
            files=[("files", ("test.jpg", sample_image_bytes, "image/jpeg"))]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["uploaded"]) == 1
        assert data["uploaded"][0]["filename"] == "test.jpg"
    
    def test_upload_multiple_images(self, client, session_id, sample_image_bytes):
        """Test uploading multiple images"""
        files = [
            ("files", (f"test{i}.jpg", sample_image_bytes, "image/jpeg"))
            for i in range(3)
        ]
        
        response = client.post(
            f"/api/upload/{session_id}",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
    
    def test_upload_to_nonexistent_session(self, client, sample_image_bytes):
        """Test uploading to a nonexistent session"""
        response = client.post(
            "/api/upload/nonexistent",
            files=[("files", ("test.jpg", sample_image_bytes, "image/jpeg"))]
        )
        
        assert response.status_code == 404
    
    def test_get_images(self, client, session_id, sample_image_bytes):
        """Test getting list of images"""
        # Upload an image first
        client.post(
            f"/api/upload/{session_id}",
            files=[("files", ("test.jpg", sample_image_bytes, "image/jpeg"))]
        )
        
        response = client.get(f"/api/images/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) == 1
    
    def test_get_single_image(self, client, session_id, sample_image_bytes):
        """Test getting a single image"""
        # Upload an image first
        upload_response = client.post(
            f"/api/upload/{session_id}",
            files=[("files", ("test.jpg", sample_image_bytes, "image/jpeg"))]
        )
        image_id = upload_response.json()["uploaded"][0]["id"]
        
        response = client.get(f"/api/image/{session_id}/{image_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == image_id
        assert data["filename"] == "test.jpg"
        assert "image" in data  # Base64 encoded
    
    def test_get_nonexistent_image(self, client, session_id):
        """Test getting a nonexistent image"""
        response = client.get(f"/api/image/{session_id}/nonexistent")
        
        assert response.status_code == 404


class TestReportEndpoints:
    """Tests for report endpoints"""
    
    def test_get_report_not_processed(self, client, session_id, sample_image_bytes):
        """Test getting a report for an unprocessed image"""
        # Upload an image
        upload_response = client.post(
            f"/api/upload/{session_id}",
            files=[("files", ("test.jpg", sample_image_bytes, "image/jpeg"))]
        )
        image_id = upload_response.json()["uploaded"][0]["id"]
        
        # Try to get report before processing
        response = client.get(f"/api/report/{session_id}/{image_id}")
        
        assert response.status_code == 404
    
    def test_get_all_reports_empty(self, client, session_id):
        """Test getting reports when none exist"""
        response = client.get(f"/api/reports/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["reports"] == []


class TestExportEndpoints:
    """Tests for export endpoints"""
    
    def test_export_json(self, client, session_id):
        """Test exporting reports as JSON"""
        response = client.get(f"/api/export/{session_id}?format=json")
        
        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
    
    def test_export_csv(self, client, session_id):
        """Test exporting reports as CSV"""
        response = client.get(f"/api/export/{session_id}?format=csv")
        
        assert response.status_code == 200
    
    def test_export_invalid_format(self, client, session_id):
        """Test exporting with invalid format"""
        response = client.get(f"/api/export/{session_id}?format=invalid")
        
        assert response.status_code == 400


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_returns_api_info(self, client):
        """Test that root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "version" in data
