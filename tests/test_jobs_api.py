"""
Tests for the Jobs API endpoints
"""
import pytest
import sys
import time
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Skip all tests if core dependencies are missing
try:
    from fastapi.testclient import TestClient
    from src.main import app
    from src.dependencies import get_job_manager
    from src.services.job_manager import JobStatus
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
def job_manager():
    """Get the job manager instance"""
    if not DEPS_AVAILABLE:
        pytest.skip(SKIP_REASON)
    return get_job_manager()


@pytest.fixture
def sample_job(job_manager):
    """Create a sample job for testing"""
    job = job_manager.create_job("test-session-123", total_items=5)
    return job


@pytest.fixture
def completed_job(job_manager):
    """Create a completed job for testing"""
    job = job_manager.create_job("test-session-456", total_items=3)
    job_manager.mark_running(job.job_id)
    job_manager.add_result(job.job_id, {"image_id": "img1", "status": "success"})
    job_manager.add_result(job.job_id, {"image_id": "img2", "status": "success"})
    job_manager.add_result(job.job_id, {"image_id": "img3", "status": "error", "error": "test"})
    job_manager.update_progress(job.job_id, processed=3, successful=2, failed=1)
    job_manager.mark_completed(job.job_id)
    return job


class TestJobStatusEndpoint:
    """Tests for GET /api/jobs/{job_id}"""
    
    def test_get_pending_job_status(self, client, sample_job):
        """Test getting status of a pending job"""
        response = client.get(f"/api/jobs/{sample_job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == sample_job.job_id
        assert data["status"] == "pending"
        assert data["progress"]["total"] == 5
        assert data["progress"]["processed"] == 0
        assert data["progress"]["percentage"] == 0.0
    
    def test_get_running_job_status(self, client, sample_job, job_manager):
        """Test getting status of a running job"""
        job_manager.mark_running(sample_job.job_id)
        job_manager.update_progress(sample_job.job_id, processed=2, successful=2, failed=0)
        
        response = client.get(f"/api/jobs/{sample_job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "running"
        assert data["started_at"] is not None
        assert data["progress"]["processed"] == 2
        assert data["progress"]["percentage"] == 40.0
    
    def test_get_completed_job_status(self, client, completed_job):
        """Test getting status of a completed job"""
        response = client.get(f"/api/jobs/{completed_job.job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["progress"]["successful"] == 2
        assert data["progress"]["failed"] == 1
        # Results should be included for completed jobs
        assert "results" in data
        assert len(data["results"]) == 3
    
    def test_get_nonexistent_job(self, client):
        """Test getting status of a nonexistent job"""
        response = client.get("/api/jobs/nonexistent-job-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestJobResultsEndpoint:
    """Tests for GET /api/jobs/{job_id}/results"""
    
    def test_get_completed_job_results(self, client, completed_job):
        """Test getting results of a completed job"""
        response = client.get(f"/api/jobs/{completed_job.job_id}/results")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == completed_job.job_id
        assert len(data["results"]) == 3
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] == 2
        assert data["summary"]["failed"] == 1
    
    def test_get_results_of_pending_job(self, client, sample_job):
        """Test that getting results of a pending job fails"""
        response = client.get(f"/api/jobs/{sample_job.job_id}/results")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()
    
    def test_get_results_of_running_job(self, client, sample_job, job_manager):
        """Test that getting results of a running job fails"""
        job_manager.mark_running(sample_job.job_id)
        
        response = client.get(f"/api/jobs/{sample_job.job_id}/results")
        
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()
    
    def test_get_results_nonexistent_job(self, client):
        """Test getting results of a nonexistent job"""
        response = client.get("/api/jobs/nonexistent-job-id/results")
        
        assert response.status_code == 404


class TestJobCancelEndpoint:
    """Tests for POST /api/jobs/{job_id}/cancel"""
    
    def test_cancel_pending_job(self, client, sample_job):
        """Test cancelling a pending job"""
        response = client.post(f"/api/jobs/{sample_job.job_id}/cancel")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "cancelled"
        assert data["job_id"] == sample_job.job_id
    
    def test_cancel_running_job(self, client, sample_job, job_manager):
        """Test cancelling a running job"""
        job_manager.mark_running(sample_job.job_id)
        
        response = client.post(f"/api/jobs/{sample_job.job_id}/cancel")
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
    
    def test_cannot_cancel_completed_job(self, client, completed_job):
        """Test that completed jobs cannot be cancelled"""
        response = client.post(f"/api/jobs/{completed_job.job_id}/cancel")
        
        assert response.status_code == 400
        assert "cannot cancel" in response.json()["detail"].lower()
    
    def test_cancel_nonexistent_job(self, client):
        """Test cancelling a nonexistent job"""
        response = client.post("/api/jobs/nonexistent-job-id/cancel")
        
        assert response.status_code == 404


class TestJobDeleteEndpoint:
    """Tests for DELETE /api/jobs/{job_id}"""
    
    def test_delete_completed_job(self, client, completed_job, job_manager):
        """Test deleting a completed job"""
        job_id = completed_job.job_id
        
        response = client.delete(f"/api/jobs/{job_id}")
        
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        
        # Verify job is deleted
        assert job_manager.get_job(job_id) is None
    
    def test_delete_cancelled_job(self, client, sample_job, job_manager):
        """Test deleting a cancelled job"""
        job_manager.cancel_job(sample_job.job_id)
        
        response = client.delete(f"/api/jobs/{sample_job.job_id}")
        
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
    
    def test_cannot_delete_running_job(self, client, sample_job, job_manager):
        """Test that running jobs cannot be deleted"""
        job_manager.mark_running(sample_job.job_id)
        
        response = client.delete(f"/api/jobs/{sample_job.job_id}")
        
        assert response.status_code == 400
    
    def test_cannot_delete_pending_job(self, client, sample_job):
        """Test that pending jobs cannot be deleted"""
        response = client.delete(f"/api/jobs/{sample_job.job_id}")
        
        assert response.status_code == 400
    
    def test_delete_nonexistent_job(self, client):
        """Test deleting a nonexistent job"""
        response = client.delete("/api/jobs/nonexistent-job-id")
        
        assert response.status_code == 404


class TestSessionJobsEndpoint:
    """Tests for GET /api/jobs/session/{session_id}"""
    
    def test_get_session_jobs(self, client, job_manager):
        """Test getting all jobs for a session"""
        session_id = "test-session-xyz"
        job_manager.create_job(session_id, total_items=5)
        job_manager.create_job(session_id, total_items=10)
        job_manager.create_job("other-session", total_items=3)
        
        response = client.get(f"/api/jobs/session/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert len(data["jobs"]) == 2
        for job in data["jobs"]:
            assert job["session_id"] == session_id
    
    def test_get_session_jobs_empty(self, client):
        """Test getting jobs for a session with no jobs"""
        response = client.get("/api/jobs/session/nonexistent-session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["jobs"] == []


class TestJobStatsEndpoint:
    """Tests for GET /api/jobs/"""
    
    def test_get_job_stats(self, client, job_manager):
        """Test getting job manager statistics"""
        # Create some jobs with different statuses
        job1 = job_manager.create_job("session-1", total_items=5)
        job2 = job_manager.create_job("session-2", total_items=5)
        job_manager.mark_running(job2.job_id)
        
        response = client.get("/api/jobs/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_jobs" in data
        assert "by_status" in data
        assert "parallel_enabled" in data
        assert "max_concurrent_jobs" in data


class TestProcessAllWithJobs:
    """Tests for the modified /process-all endpoint with background jobs"""
    
    @pytest.fixture
    def session_with_images(self, client):
        """Create a session with uploaded images"""
        # Create session
        response = client.post("/api/session/create", data={"test_type": "SIMUFSC"})
        session_id = response.json()["session_id"]
        
        # Create a simple test image
        import numpy as np
        import cv2
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        _, buffer = cv2.imencode('.jpg', img)
        image_bytes = buffer.tobytes()
        
        # Upload images
        for i in range(3):
            client.post(
                f"/api/upload/{session_id}",
                files={"file": (f"test_{i}.jpg", image_bytes, "image/jpeg")}
            )
        
        return session_id
    
    def test_process_all_returns_job_id(self, client, session_with_images):
        """Test that /process-all returns a job_id immediately"""
        response = client.post(
            f"/api/process-all/{session_with_images}",
            data={
                "fs_model": "YoloV8/first_stage/general_fs.pt",
                "ss_model": "YoloV8/second_stage/general_ss_v2.pt",
                "fs_threshold": "0.5",
                "ss_threshold": "0.5"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "accepted"
        assert "job_id" in data
        assert "poll_url" in data
        assert data["total_images"] == 3
    
    def test_process_all_empty_session(self, client):
        """Test that /process-all fails with empty session"""
        # Create empty session
        response = client.post("/api/session/create", data={"test_type": "SIMUFSC"})
        session_id = response.json()["session_id"]
        
        response = client.post(
            f"/api/process-all/{session_id}",
            data={
                "fs_model": "YoloV8/first_stage/general_fs.pt",
                "ss_model": "YoloV8/second_stage/general_ss_v2.pt"
            }
        )
        
        assert response.status_code == 400
        assert "no images" in response.json()["detail"].lower()
