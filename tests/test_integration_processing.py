"""
Integration tests for the image processing pipeline.

These tests load real images and run them through the full detection pipeline
to verify that the models and processing code work correctly together.

These tests require:
- The actual model files to be present
- Example images to be present
- Sufficient memory to load models
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestProcessingIntegration:
    """Integration tests that run the full processing pipeline."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent
    
    @pytest.fixture
    def example_image_path(self, project_root) -> Path:
        return project_root / "exemple_images" / "ps_alunos" / "ps_alunos.jpg"
    
    @pytest.fixture
    def fs_model_path(self, project_root) -> Path:
        return project_root / "models" / "YoloV8" / "first_stage" / "general_fs.pt"
    
    @pytest.fixture
    def ss_model_path(self, project_root) -> Path:
        return project_root / "models" / "YoloV8" / "second_stage" / "general_ss_v2.pt"
    
    @pytest.fixture
    def processing_service(self, project_root):
        """Create a ProcessingService instance."""
        from services.processing import ProcessingService
        service = ProcessingService()
        service.initialize()
        return service
    
    def test_files_exist(self, example_image_path, fs_model_path, ss_model_path):
        """Verify all required files exist before running tests."""
        assert example_image_path.exists(), f"Example image not found: {example_image_path}"
        assert fs_model_path.exists(), f"First stage model not found: {fs_model_path}"
        assert ss_model_path.exists(), f"Second stage model not found: {ss_model_path}"
    
    def test_process_image_returns_valid_structure(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that processing an image returns the expected structure."""
        from core.definitions import TestType
        
        # Load image bytes
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Process image
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        # Verify result structure
        assert "processed_image" in result, "Result should have 'processed_image'"
        assert "detections" in result, "Result should have 'detections'"
        assert "blocks" in result, "Result should have 'blocks'"
        assert "report" in result, "Result should have 'report'"
        
        # Verify processed_image is bytes
        assert isinstance(result["processed_image"], bytes), "processed_image should be bytes"
        assert len(result["processed_image"]) > 0, "processed_image should not be empty"
        
        # Verify detections is a list
        assert isinstance(result["detections"], list), "detections should be a list"
    
    def test_process_image_detects_first_stage_objects(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that first stage detection finds expected objects."""
        from core.definitions import TestType
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        detections = result["detections"]
        
        # Filter first stage detections
        first_stage = [d for d in detections if d["stage"] == "first"]
        
        # Should have detected at least one first stage object
        assert len(first_stage) > 0, "Should detect at least one first stage object"
        
        # Check first stage detection structure
        for det in first_stage:
            assert "class_id" in det, "Detection should have class_id"
            assert "class_name" in det, "Detection should have class_name"
            assert "confidence" in det, "Detection should have confidence"
            assert "bbox" in det, "Detection should have bbox"
            assert 0 <= det["confidence"] <= 1, "Confidence should be between 0 and 1"
            
            # Check bbox structure
            bbox = det["bbox"]
            assert "x1" in bbox and "y1" in bbox and "x2" in bbox and "y2" in bbox
            assert bbox["x1"] < bbox["x2"], "x1 should be less than x2"
            assert bbox["y1"] < bbox["y2"], "y1 should be less than y2"
    
    def test_process_image_detects_second_stage_objects(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that second stage detection finds expected objects (balls)."""
        from core.definitions import TestType
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        detections = result["detections"]
        
        # Filter second stage detections
        second_stage = [d for d in detections if d["stage"] == "second"]
        
        # Should have detected balls in second stage
        assert len(second_stage) > 0, "Should detect balls in second stage"
        
        # Check for expected class names (selected/unselected balls)
        class_names = {d["class_name"] for d in second_stage}
        expected_classes = {"SELECTED_BALL", "UNSELECTED_BALL"}
        
        # At least one type of ball should be detected
        assert len(class_names & expected_classes) > 0, \
            f"Expected to find balls. Found classes: {class_names}"
    
    def test_process_image_builds_blocks(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that processing builds TestBlocks from detections."""
        from core.definitions import TestType
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        blocks = result["blocks"]
        
        # Blocks should be created (could be None if no detections)
        # But with the example image, we expect blocks
        assert blocks is not None, "Should have created blocks from detections"
    
    def test_process_image_builds_report(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that processing builds a report from detections."""
        from core.definitions import TestType
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        report = result["report"]
        
        # Report should exist for this image
        assert report is not None, "Should have created a report"
        
        # Report should have questions attribute (could be dict or object)
        if isinstance(report, dict):
            assert "questions" in report, "Report dict should have questions"
        else:
            assert hasattr(report, "questions") or hasattr(report, "__dict__"), \
                "Report object should have questions attribute"
    
    def test_processed_image_is_valid_jpeg(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that the processed image is a valid JPEG."""
        from core.definitions import TestType
        import cv2
        import numpy as np
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        processed_bytes = result["processed_image"]
        
        # JPEG magic bytes
        assert processed_bytes[:2] == b'\xff\xd8', "Should be valid JPEG"
        
        # Can be decoded back to image
        nparr = np.frombuffer(processed_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        assert img is not None, "Should be decodable as image"
        assert img.shape[0] > 0 and img.shape[1] > 0, "Image should have valid dimensions"
    
    def test_detection_count_reasonable(
        self,
        processing_service,
        example_image_path,
        fs_model_path,
        ss_model_path
    ):
        """Test that detection counts are reasonable for the example image."""
        from core.definitions import TestType
        
        with open(example_image_path, 'rb') as f:
            image_bytes = f.read()
        
        result = processing_service.process_image(
            image_bytes=image_bytes,
            filename=example_image_path.name,
            test_type=TestType.PS_ALUNOS,
            fs_model_path=str(fs_model_path),
            ss_model_path=str(ss_model_path),
            fs_threshold=0.5,
            ss_threshold=0.5
        )
        
        detections = result["detections"]
        first_stage = [d for d in detections if d["stage"] == "first"]
        second_stage = [d for d in detections if d["stage"] == "second"]
        
        print(f"\n=== Detection Summary ===")
        print(f"First stage detections: {len(first_stage)}")
        print(f"Second stage detections: {len(second_stage)}")
        print(f"Total detections: {len(detections)}")
        
        # First stage should detect question blocks and CPF block
        # For ps_alunos, expect at least 1 block
        assert len(first_stage) >= 1, \
            f"Expected at least 1 first stage detection, got {len(first_stage)}"
        
        # Second stage should detect many balls
        # For a typical answer sheet, expect many balls
        assert len(second_stage) >= 10, \
            f"Expected at least 10 second stage detections (balls), got {len(second_stage)}"
        
        # Print class breakdown
        print("\nFirst stage classes:")
        for det in first_stage:
            print(f"  - {det['class_name']}: {det['confidence']:.2f}")
        
        print(f"\nSecond stage class counts:")
        from collections import Counter
        class_counts = Counter(d["class_name"] for d in second_stage)
        for class_name, count in class_counts.items():
            print(f"  - {class_name}: {count}")


class TestProcessingServiceInit:
    """Tests for ProcessingService initialization."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent
    
    def test_service_initializes(self, project_root):
        """Test that ProcessingService can be initialized."""
        from services.processing import ProcessingService
        
        service = ProcessingService()
        service.initialize()
        assert service is not None
    
    def test_service_lists_available_models(self, project_root):
        """Test that service can list available models."""
        from services.processing import ProcessingService
        
        service = ProcessingService()
        service.initialize()
        models = service.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0, "Should find at least one model"
        
        # Check model structure
        for model in models:
            assert "name" in model or "path" in model, "Model should have name or path"


class TestModelLoading:
    """Tests specifically for model loading."""
    
    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent
    
    def test_yolo_model_loads(self, project_root):
        """Test that YOLO model can be loaded."""
        from core.model import DetectionModel
        from core.definitions import Stage, TestType
        
        model_path = project_root / "models" / "YoloV8" / "first_stage" / "general_fs.pt"
        
        if not model_path.exists():
            pytest.skip(f"Model not found: {model_path}")
        
        model = DetectionModel.from_models_path(
            str(model_path),
            Stage.FIRST,
            TestType.PS_ALUNOS
        )
        
        assert model is not None
        assert model.label_map is not None
    
    def test_model_has_label_map_with_detections(self, project_root):
        """Test that loaded model has label map with detections list."""
        from core.model import DetectionModel
        from core.definitions import Stage, TestType
        
        model_path = project_root / "models" / "YoloV8" / "first_stage" / "general_fs.pt"
        
        if not model_path.exists():
            pytest.skip(f"Model not found: {model_path}")
        
        model = DetectionModel.from_models_path(
            str(model_path),
            Stage.FIRST,
            TestType.PS_ALUNOS
        )
        
        assert model.label_map is not None, "Model should have label_map"
        assert hasattr(model.label_map, 'detections'), "LabelMap should have 'detections' attribute"
        assert len(model.label_map.detections) > 0, "LabelMap should have detection types"
        
        # Verify we can access detection names
        for det_type in model.label_map.detections:
            assert hasattr(det_type, 'name'), "Detection type should have 'name'"
            print(f"Detection type: {det_type.name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
