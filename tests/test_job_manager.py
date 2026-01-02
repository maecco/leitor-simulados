"""
Tests for the JobManager service
"""
import pytest
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.services.job_manager import (
    JobManager,
    Job,
    JobStatus,
    JobProgress
)


class TestJobProgress:
    """Tests for the JobProgress dataclass"""
    
    def test_progress_default(self):
        """Test default progress values"""
        progress = JobProgress()
        
        assert progress.total == 0
        assert progress.processed == 0
        assert progress.successful == 0
        assert progress.failed == 0
    
    def test_progress_percentage_zero_total(self):
        """Test percentage with zero total (avoid division by zero)"""
        progress = JobProgress(total=0, processed=0)
        assert progress.percentage == 0.0
    
    def test_progress_percentage_calculation(self):
        """Test percentage calculation"""
        progress = JobProgress(total=100, processed=50)
        assert progress.percentage == 50.0
        
        progress = JobProgress(total=3, processed=1)
        assert progress.percentage == 33.3
    
    def test_progress_to_dict(self):
        """Test progress serialization"""
        progress = JobProgress(total=10, processed=5, successful=4, failed=1)
        data = progress.to_dict()
        
        assert data["total"] == 10
        assert data["processed"] == 5
        assert data["successful"] == 4
        assert data["failed"] == 1
        assert data["percentage"] == 50.0


class TestJob:
    """Tests for the Job dataclass"""
    
    def test_job_creation(self):
        """Test creating a job"""
        job = Job(
            job_id="test-job-1",
            session_id="session-123",
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        assert job.job_id == "test-job-1"
        assert job.session_id == "session-123"
        assert job.status == JobStatus.PENDING
        assert job.started_at is None
        assert job.completed_at is None
        assert job.results == []
        assert job.error is None
    
    def test_job_to_dict(self):
        """Test job serialization"""
        job = Job(
            job_id="test-job-2",
            session_id="session-456",
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            started_at=datetime.now()
        )
        job.progress = JobProgress(total=5, processed=2, successful=2, failed=0)
        
        data = job.to_dict()
        
        assert data["job_id"] == "test-job-2"
        assert data["session_id"] == "session-456"
        assert data["status"] == "running"
        assert data["started_at"] is not None
        assert data["completed_at"] is None
        assert "progress" in data
        assert data["progress"]["total"] == 5
    
    def test_job_duration_not_started(self):
        """Test duration for job that hasn't started"""
        job = Job(
            job_id="test",
            session_id="session",
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        
        data = job.to_dict()
        assert data["duration_seconds"] is None
    
    def test_job_duration_running(self):
        """Test duration for running job"""
        job = Job(
            job_id="test",
            session_id="session",
            status=JobStatus.RUNNING,
            created_at=datetime.now(),
            started_at=datetime.now()
        )
        
        time.sleep(0.1)  # Small delay
        data = job.to_dict()
        
        assert data["duration_seconds"] is not None
        assert data["duration_seconds"] >= 0.1


class TestJobManager:
    """Tests for the JobManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh JobManager for each test"""
        mgr = JobManager(use_parallel=False)
        yield mgr
        mgr.shutdown()
    
    def test_create_job(self, manager):
        """Test creating a new job"""
        job = manager.create_job("session-123", total_items=10)
        
        assert job is not None
        assert job.session_id == "session-123"
        assert job.status == JobStatus.PENDING
        assert job.progress.total == 10
    
    def test_get_job(self, manager):
        """Test retrieving a job"""
        created_job = manager.create_job("session-123", total_items=5)
        
        retrieved_job = manager.get_job(created_job.job_id)
        
        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id
    
    def test_get_nonexistent_job(self, manager):
        """Test retrieving a job that doesn't exist"""
        job = manager.get_job("nonexistent-id")
        assert job is None
    
    def test_get_jobs_for_session(self, manager):
        """Test getting all jobs for a session"""
        manager.create_job("session-A", total_items=5)
        manager.create_job("session-A", total_items=10)
        manager.create_job("session-B", total_items=3)
        
        jobs_a = manager.get_jobs_for_session("session-A")
        jobs_b = manager.get_jobs_for_session("session-B")
        
        assert len(jobs_a) == 2
        assert len(jobs_b) == 1
    
    def test_update_progress(self, manager):
        """Test updating job progress"""
        job = manager.create_job("session-123", total_items=10)
        
        manager.update_progress(job.job_id, processed=5, successful=4, failed=1)
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.progress.processed == 5
        assert updated_job.progress.successful == 4
        assert updated_job.progress.failed == 1
    
    def test_add_result(self, manager):
        """Test adding results to a job"""
        job = manager.create_job("session-123", total_items=2)
        
        manager.add_result(job.job_id, {"image_id": "img1", "status": "success"})
        manager.add_result(job.job_id, {"image_id": "img2", "status": "error"})
        
        updated_job = manager.get_job(job.job_id)
        assert len(updated_job.results) == 2
        assert updated_job.results[0]["image_id"] == "img1"
    
    def test_mark_running(self, manager):
        """Test marking a job as running"""
        job = manager.create_job("session-123", total_items=5)
        
        manager.mark_running(job.job_id)
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.RUNNING
        assert updated_job.started_at is not None
    
    def test_mark_completed(self, manager):
        """Test marking a job as completed"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        
        manager.mark_completed(job.job_id)
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None
    
    def test_mark_failed(self, manager):
        """Test marking a job as failed"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        
        manager.mark_failed(job.job_id, "Something went wrong")
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert updated_job.error == "Something went wrong"
        assert updated_job.completed_at is not None
    
    def test_cancel_pending_job(self, manager):
        """Test cancelling a pending job"""
        job = manager.create_job("session-123", total_items=5)
        
        result = manager.cancel_job(job.job_id)
        
        assert result is True
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.CANCELLED
    
    def test_cancel_running_job(self, manager):
        """Test cancelling a running job"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        
        result = manager.cancel_job(job.job_id)
        
        assert result is True
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.CANCELLED
    
    def test_cannot_cancel_completed_job(self, manager):
        """Test that completed jobs cannot be cancelled"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        manager.mark_completed(job.job_id)
        
        result = manager.cancel_job(job.job_id)
        
        assert result is False
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
    
    def test_delete_completed_job(self, manager):
        """Test deleting a completed job"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        manager.mark_completed(job.job_id)
        
        result = manager.delete_job(job.job_id)
        
        assert result is True
        assert manager.get_job(job.job_id) is None
    
    def test_cannot_delete_running_job(self, manager):
        """Test that running jobs cannot be deleted"""
        job = manager.create_job("session-123", total_items=5)
        manager.mark_running(job.job_id)
        
        result = manager.delete_job(job.job_id)
        
        assert result is False
        assert manager.get_job(job.job_id) is not None
    
    def test_is_job_cancelled(self, manager):
        """Test checking if a job is cancelled"""
        job = manager.create_job("session-123", total_items=5)
        
        assert manager.is_job_cancelled(job.job_id) is False
        
        manager.cancel_job(job.job_id)
        
        assert manager.is_job_cancelled(job.job_id) is True
    
    def test_get_results(self, manager):
        """Test getting results for a job"""
        job = manager.create_job("session-123", total_items=2)
        manager.add_result(job.job_id, {"id": "1"})
        manager.add_result(job.job_id, {"id": "2"})
        
        results = manager.get_results(job.job_id)
        
        assert len(results) == 2
        # Ensure it returns a copy
        results.append({"id": "3"})
        assert len(manager.get_results(job.job_id)) == 2
    
    def test_get_stats(self, manager):
        """Test getting job manager statistics"""
        manager.create_job("session-1", total_items=5)
        job2 = manager.create_job("session-2", total_items=5)
        manager.mark_running(job2.job_id)
        
        stats = manager.get_stats()
        
        assert stats["total_jobs"] == 2
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["running"] == 1
        assert stats["parallel_enabled"] is False
    
    def test_submit_job_executes_task(self, manager):
        """Test that submit_job executes the task function"""
        job = manager.create_job("session-123", total_items=1)
        task_executed = []
        
        def test_task(job_id):
            task_executed.append(job_id)
        
        manager.submit_job(job.job_id, test_task)
        
        # Wait for task to complete
        time.sleep(0.5)
        
        assert len(task_executed) == 1
        assert task_executed[0] == job.job_id
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.COMPLETED
    
    def test_submit_job_handles_exception(self, manager):
        """Test that submit_job handles task exceptions"""
        job = manager.create_job("session-123", total_items=1)
        
        def failing_task(job_id):
            raise ValueError("Task failed!")
        
        manager.submit_job(job.job_id, failing_task)
        
        # Wait for task to complete
        time.sleep(0.5)
        
        updated_job = manager.get_job(job.job_id)
        assert updated_job.status == JobStatus.FAILED
        assert "Task failed!" in updated_job.error
    
    def test_submit_job_with_args(self, manager):
        """Test submit_job passes arguments correctly"""
        job = manager.create_job("session-123", total_items=1)
        received_args = []
        
        def task_with_args(job_id, arg1, arg2, kwarg1=None):
            received_args.append((arg1, arg2, kwarg1))
        
        manager.submit_job(job.job_id, task_with_args, "value1", "value2", kwarg1="kwvalue")
        
        # Wait for task to complete
        time.sleep(0.5)
        
        assert len(received_args) == 1
        assert received_args[0] == ("value1", "value2", "kwvalue")


class TestJobManagerParallel:
    """Tests for JobManager with parallel processing enabled"""
    
    @pytest.fixture
    def manager_parallel(self):
        """Create a JobManager with parallel processing"""
        mgr = JobManager(use_parallel=True)
        yield mgr
        mgr.shutdown()
    
    def test_parallel_initialization(self, manager_parallel):
        """Test that parallel manager initializes correctly"""
        stats = manager_parallel.get_stats()
        assert stats["parallel_enabled"] is True
    
    def test_parallel_basic_operations(self, manager_parallel):
        """Test basic operations work with parallel enabled"""
        job = manager_parallel.create_job("session-123", total_items=5)
        
        assert job is not None
        assert manager_parallel.get_job(job.job_id) is not None
