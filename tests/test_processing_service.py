"""
Tests for the ProcessingService
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Skip tests if core dependencies are missing
try:
    from backend.services.processing import ProcessingService, ModelCache
    DEPS_AVAILABLE = True
except ImportError as e:
    DEPS_AVAILABLE = False
    SKIP_REASON = f"Core dependencies not available: {e}"


pytestmark = pytest.mark.skipif(not DEPS_AVAILABLE, reason="Core dependencies not available")


class TestModelCache:
    """Tests for the ModelCache class"""
    
    @pytest.fixture
    def cache(self):
        if not DEPS_AVAILABLE:
            pytest.skip(SKIP_REASON)
        return ModelCache()
    
    def test_cache_creation(self, cache):
        """Test creating a model cache"""
        assert cache._models == {}
    
    def test_cache_clear(self, cache):
        """Test clearing the cache"""
        cache._models["test"] = "model"
        
        cache.clear()
        
        assert cache._models == {}


class TestProcessingService:
    """Tests for the ProcessingService class"""
    
    @pytest.fixture
    def service(self):
        """Create a ProcessingService instance"""
        if not DEPS_AVAILABLE:
            pytest.skip(SKIP_REASON)
        return ProcessingService()
    
    def test_service_creation(self, service):
        """Test creating a processing service"""
        assert service._model_cache is not None
        assert service._available_models == []
    
    def test_get_available_models_empty(self, service):
        """Test getting models before initialization"""
        models = service.get_available_models()
        assert models == []
    
    def test_get_models_for_stage(self, service):
        """Test filtering models by stage"""
        service._available_models = [
            {"name": "model1", "target_stage": "FIRST"},
            {"name": "model2", "target_stage": "SECOND"},
            {"name": "model3", "target_stage": "BOTH"},
        ]
        
        first_stage = service.get_models_for_stage("FIRST")
        assert len(first_stage) == 2  # model1 and model3
        
        second_stage = service.get_models_for_stage("SECOND")
        assert len(second_stage) == 2  # model2 and model3
    
    def test_export_to_csv_empty(self, service):
        """Test CSV export with no reports"""
        result = service.export_to_csv([])
        assert result == ""
    
    def test_export_to_csv(self, service):
        """Test CSV export with reports"""
        reports = [
            {
                "filename": "test1.jpg",
                "report": {
                    "owner_cpf": "12345678901",
                    "questions": [
                        {"number": 1, "answer": "A"},
                        {"number": 2, "answer": "B"}
                    ]
                }
            },
            {
                "filename": "test2.jpg",
                "report": {
                    "owner_cpf": "09876543210",
                    "questions": [
                        {"number": 1, "answer": "C"},
                        {"number": 2, "answer": "D"}
                    ]
                }
            }
        ]
        
        result = service.export_to_csv(reports)
        
        assert "filename" in result
        assert "cpf" in result
        assert "Q1" in result
        assert "Q2" in result
        assert "12345678901" in result
        assert "09876543210" in result
        assert "test1.jpg" in result
        assert "test2.jpg" in result


class TestProcessingServiceIntegration:
    """Integration tests for ProcessingService (require models)"""
    
    @pytest.fixture
    def service(self):
        """Create and initialize a processing service"""
        service = ProcessingService()
        # Only initialize if models directory exists
        models_path = PROJECT_ROOT / "models"
        if models_path.exists():
            service.initialize()
        return service
    
    @pytest.mark.skipif(
        not (PROJECT_ROOT / "models").exists(),
        reason="Models directory not found"
    )
    def test_initialize_scans_models(self, service):
        """Test that initialization scans for models"""
        # After initialization, should have found some models
        models = service.get_available_models()
        # Just check it ran without error; may or may not find models
        assert isinstance(models, list)
    
    @pytest.mark.skipif(
        not (PROJECT_ROOT / "models" / "YoloV8").exists(),
        reason="YOLOv8 models not found"
    )
    def test_model_info_structure(self, service):
        """Test that model info has correct structure"""
        service.initialize()
        models = service.get_available_models()
        
        if models:
            model = models[0]
            assert "name" in model
            assert "model_type" in model
            assert "target_stage" in model
            assert "rel_path" in model
