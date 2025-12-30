"""
API Client for Leitor de Simulados Server
Handles all HTTP communication with the backend
"""
import requests
from pathlib import Path
from typing import Optional


class APIClient:
    """HTTP client for communicating with the Leitor de Simulados server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 30
    
    def _url(self, path: str) -> str:
        """Build full URL"""
        return f"{self.base_url.rstrip('/')}{path}"
    
    def _handle_response(self, response: requests.Response) -> dict:
        """Handle API response"""
        if response.status_code >= 400:
            try:
                error = response.json().get("detail", "Unknown error")
            except:
                error = response.text
            raise APIError(f"HTTP {response.status_code}: {error}")
        return response.json()
    
    # =========================================================================
    # Session endpoints
    # =========================================================================
    
    def create_session(self, test_type: str) -> dict:
        """Create a new processing session"""
        response = requests.post(
            self._url("/api/session/create"),
            data={"test_type": test_type},
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def get_session(self, session_id: str) -> dict:
        """Get session information"""
        response = requests.get(
            self._url(f"/api/session/{session_id}"),
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def delete_session(self, session_id: str) -> dict:
        """Delete a session"""
        response = requests.delete(
            self._url(f"/api/session/{session_id}"),
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    # =========================================================================
    # Model endpoints
    # =========================================================================
    
    def get_models(self) -> list:
        """Get available detection models"""
        response = requests.get(
            self._url("/api/models"),
            timeout=self.timeout
        )
        result = self._handle_response(response)
        return result.get("models", [])
    
    # =========================================================================
    # Image endpoints
    # =========================================================================
    
    def upload_images(self, session_id: str, file_paths: list) -> dict:
        """Upload images to a session"""
        files = []
        for path in file_paths:
            path = Path(path)
            if path.exists():
                files.append(
                    ("files", (path.name, open(path, "rb"), "image/jpeg"))
                )
        
        try:
            response = requests.post(
                self._url(f"/api/upload/{session_id}"),
                files=files,
                timeout=60  # Longer timeout for uploads
            )
            return self._handle_response(response)
        finally:
            # Close file handles
            for _, file_tuple in files:
                file_tuple[1].close()
    
    def get_images(self, session_id: str) -> dict:
        """Get list of images in a session"""
        response = requests.get(
            self._url(f"/api/images/{session_id}"),
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def get_image(self, session_id: str, image_id: str, with_detections: bool = False) -> dict:
        """Get a specific image"""
        response = requests.get(
            self._url(f"/api/image/{session_id}/{image_id}"),
            params={"with_detections": with_detections},
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    # =========================================================================
    # Processing endpoints
    # =========================================================================
    
    def process_image(
        self,
        session_id: str,
        image_id: str,
        fs_model: str,
        ss_model: str,
        fs_threshold: float = 0.5,
        ss_threshold: float = 0.5
    ) -> dict:
        """Process a single image"""
        response = requests.post(
            self._url(f"/api/process/{session_id}/{image_id}"),
            data={
                "fs_model": fs_model,
                "ss_model": ss_model,
                "fs_threshold": fs_threshold,
                "ss_threshold": ss_threshold
            },
            timeout=120  # Long timeout for processing
        )
        return self._handle_response(response)
    
    def process_all_images(
        self,
        session_id: str,
        fs_model: str,
        ss_model: str,
        fs_threshold: float = 0.5,
        ss_threshold: float = 0.5
    ) -> dict:
        """Process all images in a session"""
        response = requests.post(
            self._url(f"/api/process-all/{session_id}"),
            data={
                "fs_model": fs_model,
                "ss_model": ss_model,
                "fs_threshold": fs_threshold,
                "ss_threshold": ss_threshold
            },
            timeout=600  # Very long timeout for batch processing
        )
        return self._handle_response(response)
    
    # =========================================================================
    # Report endpoints
    # =========================================================================
    
    def get_report(self, session_id: str, image_id: str) -> dict:
        """Get report for a processed image"""
        response = requests.get(
            self._url(f"/api/report/{session_id}/{image_id}"),
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def get_all_reports(self, session_id: str) -> dict:
        """Get all reports for a session"""
        response = requests.get(
            self._url(f"/api/reports/{session_id}"),
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def update_answer(
        self,
        session_id: str,
        image_id: str,
        question_number: int,
        answer: str
    ) -> dict:
        """Update an answer in the report"""
        response = requests.post(
            self._url(f"/api/update-answer/{session_id}/{image_id}"),
            data={
                "question_number": question_number,
                "answer": answer
            },
            timeout=self.timeout
        )
        return self._handle_response(response)
    
    def export_reports(self, session_id: str, format: str = "json") -> dict:
        """Export all reports"""
        response = requests.get(
            self._url(f"/api/export/{session_id}"),
            params={"format": format},
            timeout=self.timeout
        )
        return self._handle_response(response)


class APIError(Exception):
    """API communication error"""
    pass
