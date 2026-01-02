"""
Job Manager Service
Handles background job tracking and execution for batch processing
"""
import uuid
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobProgress:
    """Tracks progress of a job"""
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.processed / self.total) * 100, 1)
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "percentage": self.percentage
        }


@dataclass
class Job:
    """Represents a background job"""
    job_id: str
    session_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: JobProgress = field(default_factory=JobProgress)
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress.to_dict(),
            "error": self.error,
            "duration_seconds": self._get_duration()
        }
    
    def _get_duration(self) -> Optional[float]:
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.now()
        return round((end_time - self.started_at).total_seconds(), 2)


class JobManager:
    """
    Manages background jobs for batch image processing.
    
    Features:
    - Track job status and progress
    - Execute jobs in background threads
    - Optional parallel processing with ProcessPoolExecutor
    - Progress updates during execution
    """
    
    # Maximum number of concurrent jobs
    MAX_CONCURRENT_JOBS = 3
    
    # Maximum workers for parallel image processing within a job
    MAX_PARALLEL_WORKERS = 4
    
    def __init__(self, use_parallel: bool = False):
        """
        Initialize JobManager.
        
        Args:
            use_parallel: If True, use ProcessPoolExecutor for parallel 
                         image processing within jobs (higher memory usage)
        """
        self._jobs: Dict[str, Job] = {}
        self._lock = Lock()
        self._use_parallel = use_parallel
        
        # Thread pool for running background jobs
        self._executor = ThreadPoolExecutor(
            max_workers=self.MAX_CONCURRENT_JOBS,
            thread_name_prefix="job_worker"
        )
        
        # Process pool for parallel image processing (optional)
        self._process_pool: Optional[ProcessPoolExecutor] = None
        if use_parallel:
            self._process_pool = ProcessPoolExecutor(
                max_workers=self.MAX_PARALLEL_WORKERS
            )
        
        logger.info(
            f"JobManager initialized (parallel={use_parallel}, "
            f"max_jobs={self.MAX_CONCURRENT_JOBS})"
        )
    
    def create_job(self, session_id: str, total_items: int) -> Job:
        """Create a new job and return it"""
        job_id = str(uuid.uuid4())[:8]  # Short ID for convenience
        
        job = Job(
            job_id=job_id,
            session_id=session_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(),
            progress=JobProgress(total=total_items)
        )
        
        with self._lock:
            self._jobs[job_id] = job
        
        logger.info(f"Created job {job_id} for session {session_id} ({total_items} items)")
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_jobs_for_session(self, session_id: str) -> List[Job]:
        """Get all jobs for a session"""
        with self._lock:
            return [j for j in self._jobs.values() if j.session_id == session_id]
    
    def update_progress(
        self,
        job_id: str,
        processed: int,
        successful: int,
        failed: int
    ):
        """Update job progress"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress.processed = processed
                job.progress.successful = successful
                job.progress.failed = failed
    
    def add_result(self, job_id: str, result: Dict[str, Any]):
        """Add a result to a job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.results.append(result)
    
    def mark_running(self, job_id: str):
        """Mark a job as running"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
    
    def mark_completed(self, job_id: str):
        """Mark a job as completed"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                logger.info(
                    f"Job {job_id} completed: {job.progress.successful} success, "
                    f"{job.progress.failed} failed"
                )
    
    def mark_failed(self, job_id: str, error: str):
        """Mark a job as failed"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                job.error = error
                logger.error(f"Job {job_id} failed: {error}")
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                logger.info(f"Job {job_id} cancelled")
                return True
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a completed/failed/cancelled job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                del self._jobs[job_id]
                return True
            return False
    
    def submit_job(
        self,
        job_id: str,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """
        Submit a job for background execution.
        
        Args:
            job_id: The job ID to execute
            task_func: The function to execute (should accept job_id as first arg)
            *args, **kwargs: Additional arguments for task_func
        """
        self._executor.submit(
            self._run_job_wrapper,
            job_id,
            task_func,
            *args,
            **kwargs
        )
    
    def _run_job_wrapper(
        self,
        job_id: str,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """Wrapper to handle job lifecycle"""
        try:
            self.mark_running(job_id)
            task_func(job_id, *args, **kwargs)
            self.mark_completed(job_id)
        except Exception as e:
            logger.exception(f"Job {job_id} failed with exception")
            self.mark_failed(job_id, str(e))
    
    def is_job_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job is not None and job.status == JobStatus.CANCELLED
    
    def get_results(self, job_id: str) -> List[Dict[str, Any]]:
        """Get results for a completed job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return job.results.copy()
            return []
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours"""
        cutoff = datetime.now()
        removed = 0
        
        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    age = (cutoff - job.created_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(job_id)
            
            for job_id in to_remove:
                del self._jobs[job_id]
                removed += 1
        
        if removed:
            logger.info(f"Cleaned up {removed} old jobs")
    
    def shutdown(self):
        """Shutdown the job manager and cleanup resources"""
        logger.info("Shutting down JobManager...")
        self._executor.shutdown(wait=False)
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
        logger.info("JobManager shutdown complete")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job manager statistics"""
        with self._lock:
            status_counts = {}
            for job in self._jobs.values():
                status = job.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_jobs": len(self._jobs),
                "by_status": status_counts,
                "parallel_enabled": self._use_parallel,
                "max_concurrent_jobs": self.MAX_CONCURRENT_JOBS
            }
