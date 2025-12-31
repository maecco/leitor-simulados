"""
Tests for the SessionManager service
"""
import pytest
from datetime import datetime, timedelta

from src.services.session_manager import SessionManager, Session
from src.core.definitions.enums import TestType


class TestSession:
    """Tests for the Session dataclass"""
    
    def test_session_creation(self):
        """Test creating a session"""
        session = Session(
            session_id="test-123",
            test_type=TestType.SIMUFSC,
            created_at=datetime.now()
        )
        
        assert session.session_id == "test-123"
        assert session.test_type == TestType.SIMUFSC
        assert session.images == {}
    
    def test_session_to_dict(self):
        """Test session serialization"""
        session = Session(
            session_id="test-456",
            test_type=TestType.PS_ALUNOS,
            created_at=datetime.now()
        )
        
        data = session.to_dict()
        
        assert data["session_id"] == "test-456"
        assert data["test_type"] == "PS_ALUNOS"
        assert data["image_count"] == 0
        assert data["processed_count"] == 0
        assert "created_at" in data
    
    def test_session_counts(self):
        """Test session image counting"""
        session = Session(
            session_id="test-789",
            test_type=TestType.SIMUFSC,
            created_at=datetime.now()
        )
        
        # Add some images
        session.images["img1"] = {"processed": False}
        session.images["img2"] = {"processed": True}
        session.images["img3"] = {"processed": True}
        
        data = session.to_dict()
        assert data["image_count"] == 3
        assert data["processed_count"] == 2


class TestSessionManager:
    """Tests for the SessionManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh SessionManager for each test"""
        return SessionManager()
    
    def test_create_session(self, manager):
        """Test creating a new session"""
        session_id = manager.create_session(TestType.SIMUFSC)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID format
    
    def test_get_session(self, manager):
        """Test retrieving a session"""
        session_id = manager.create_session(TestType.PS_ALUNOS)
        
        session = manager.get_session(session_id)
        
        assert session is not None
        assert session.session_id == session_id
        assert session.test_type == TestType.PS_ALUNOS
    
    def test_get_nonexistent_session(self, manager):
        """Test retrieving a session that doesn't exist"""
        session = manager.get_session("nonexistent-id")
        assert session is None
    
    def test_delete_session(self, manager):
        """Test deleting a session"""
        session_id = manager.create_session(TestType.SIMUFSC)
        
        result = manager.delete_session(session_id)
        
        assert result is True
        assert manager.get_session(session_id) is None
    
    def test_delete_nonexistent_session(self, manager):
        """Test deleting a session that doesn't exist"""
        result = manager.delete_session("nonexistent-id")
        assert result is False
    
    def test_add_image(self, manager, sample_image_bytes):
        """Test adding an image to a session"""
        session_id = manager.create_session(TestType.SIMUFSC)
        
        image_id = manager.add_image(session_id, "test.jpg", sample_image_bytes)
        
        assert image_id is not None
        assert len(image_id) == 36  # UUID format
        
        session = manager.get_session(session_id)
        assert len(session.images) == 1
        assert image_id in session.images
    
    def test_add_image_to_nonexistent_session(self, manager, sample_image_bytes):
        """Test adding an image to a session that doesn't exist"""
        image_id = manager.add_image("nonexistent", "test.jpg", sample_image_bytes)
        assert image_id is None
    
    def test_get_image(self, manager, sample_image_bytes):
        """Test retrieving an image"""
        session_id = manager.create_session(TestType.SIMUFSC)
        image_id = manager.add_image(session_id, "test.jpg", sample_image_bytes)
        
        img_data = manager.get_image(session_id, image_id)
        
        assert img_data is not None
        assert img_data["filename"] == "test.jpg"
        assert img_data["raw"] == sample_image_bytes
        assert img_data["processed"] is False
    
    def test_get_nonexistent_image(self, manager):
        """Test retrieving an image that doesn't exist"""
        session_id = manager.create_session(TestType.SIMUFSC)
        
        img_data = manager.get_image(session_id, "nonexistent")
        assert img_data is None
    
    def test_update_image_results(self, manager, sample_image_bytes):
        """Test updating image processing results"""
        session_id = manager.create_session(TestType.SIMUFSC)
        image_id = manager.add_image(session_id, "test.jpg", sample_image_bytes)
        
        result = manager.update_image_results(
            session_id, image_id,
            processed_image=b"processed_data",
            detections=[{"test": "detection"}]
        )
        
        assert result is True
        
        img_data = manager.get_image(session_id, image_id)
        assert img_data["processed"] is True
        assert img_data["processed_image"] == b"processed_data"
        assert img_data["detections"] == [{"test": "detection"}]
    
    def test_update_nonexistent_image_results(self, manager):
        """Test updating results for an image that doesn't exist"""
        session_id = manager.create_session(TestType.SIMUFSC)
        
        result = manager.update_image_results(
            session_id, "nonexistent",
            processed_image=b"data"
        )
        
        assert result is False
    
    def test_multiple_sessions(self, manager):
        """Test creating and managing multiple sessions"""
        session_ids = []
        for test_type in [TestType.SIMUFSC, TestType.PS_ALUNOS, TestType.SIMUENEM]:
            session_ids.append(manager.create_session(test_type))
        
        assert len(session_ids) == 3
        assert len(set(session_ids)) == 3  # All unique
        
        for session_id in session_ids:
            assert manager.get_session(session_id) is not None
    
    def test_cleanup_all(self, manager, sample_image_bytes):
        """Test cleaning up all sessions"""
        session_id = manager.create_session(TestType.SIMUFSC)
        manager.add_image(session_id, "test.jpg", sample_image_bytes)
        
        manager.cleanup_all()
        
        assert manager.get_session(session_id) is None
    
    def test_get_all_sessions(self, manager):
        """Test getting all sessions"""
        manager.create_session(TestType.SIMUFSC)
        manager.create_session(TestType.PS_ALUNOS)
        
        sessions = manager.get_all_sessions()
        
        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)
