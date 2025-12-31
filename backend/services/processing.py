"""
Processing Service
Handles image detection and report generation
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import io
import csv

import cv2
import numpy as np

from core.definitions.enums import TestType, Stage, ModelType
from core.definitions.question import TestReport
from core.definitions.blocks import TestBlocks
from core.image import CoreImage
from core.model import DetectionModel
from core.detection import Detection, DetectionContainer
from core.detection.label_map import LabelMap
from core.builder import Builder
from core.IO.base import Importer
from core.IO import MODELS_PATH


class ModelCache:
    """Cache for loaded detection models"""
    
    def __init__(self):
        self._models: Dict[str, DetectionModel] = {}
    
    def get_or_load(self, model_path: str, stage: Stage, test_type: TestType = TestType.NULL) -> DetectionModel:
        """Get a model from cache or load it"""
        cache_key = f"{model_path}:{stage.name}:{test_type.name}"
        
        if cache_key not in self._models:
            model = DetectionModel.from_models_path(model_path, stage, test_type)
            self._models[cache_key] = model
        
        return self._models[cache_key]
    
    def clear(self):
        """Clear the model cache"""
        self._models.clear()


class ProcessingService:
    """
    Service for processing images with detection models
    """
    
    def __init__(self):
        self._model_cache = ModelCache()
        self._available_models: List[Dict[str, Any]] = []
    
    def initialize(self):
        """Initialize the service and scan for available models"""
        self._scan_models()
    
    def _scan_models(self):
        """Scan for available model files"""
        self._available_models = []
        
        try:
            file_paths = Importer.Find.model_files()
            for path in file_paths:
                fullpath = Path(path)
                rel_path = fullpath.relative_to(MODELS_PATH)
                parts = rel_path.parts
                name, extension = parts[-1].split('.')
                
                model_type = (
                    "LEGACY" if extension == 'tflite'
                    else "EFSCANALGO" if extension == 'py'
                    else "YOLOV8"
                )
                
                target_stage = (
                    "FIRST" if 'first_stage' in path
                    else "SECOND" if 'second_stage' in path
                    else "BOTH" if 'single_stage' in path
                    else "NULL"
                )
                
                self._available_models.append({
                    "name": name,
                    "model_type": model_type,
                    "target_stage": target_stage,
                    "rel_path": str(rel_path)
                })
        except Exception as e:
            print(f"Error scanning models: {e}")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models"""
        return self._available_models
    
    def get_models_for_stage(self, stage: str) -> List[Dict[str, Any]]:
        """Get models compatible with a specific stage"""
        return [
            m for m in self._available_models
            if m["target_stage"] == stage or m["target_stage"] == "BOTH"
        ]
    
    def process_image(
        self,
        image_bytes: bytes,
        filename: str,
        test_type: TestType,
        fs_model_path: str,
        ss_model_path: str,
        fs_threshold: float = 0.5,
        ss_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Process an image through the detection pipeline
        
        Returns dict with:
        - processed_image: bytes (image with detections drawn)
        - detections: list of detection info
        - blocks: TestBlocks object
        - report: TestReport object
        """
        # Decode image from bytes
        nparr = np.frombuffer(image_bytes, np.uint8)
        raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if raw_img is None:
            raise ValueError("Could not decode image")
        
        # Create CoreImage
        core_image = CoreImage(filename, raw_img, None)
        
        # Load models
        fs_model = self._model_cache.get_or_load(fs_model_path, Stage.FIRST, test_type)
        ss_model = self._model_cache.get_or_load(ss_model_path, Stage.SECOND, test_type)
        
        # Run first stage detection
        with Detection.label_map_context(fs_model.label_map):
            core_image.make_detections_with_model(fs_model, fs_threshold)
        
        # Create crops from first stage detections
        core_image.make_cropped()
        
        # Run second stage detection on crops
        with Detection.label_map_context(ss_model.label_map):
            for crop in core_image.crops:
                crop.make_detections_with_model(ss_model, ss_threshold)
        
        # Build blocks from detections using CoreImage's to_block method
        blocks = core_image.to_block()
        
        # Build report
        report = self._build_report(blocks, test_type)
        
        # Draw detections on image
        processed_img = self._draw_detections(core_image)
        
        # Encode processed image to bytes
        _, buffer = cv2.imencode('.jpg', processed_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        processed_bytes = buffer.tobytes()
        
        # Collect detection info
        detections_info = self._collect_detections_info(core_image, fs_model, ss_model)
        
        # Cleanup
        core_image.free()
        
        return {
            "processed_image": processed_bytes,
            "detections": detections_info,
            "blocks": blocks,
            "report": report
        }
    
    def _build_report(self, blocks: TestBlocks, test_type: TestType) -> Optional[TestReport]:
        """Build a report from detected blocks"""
        if not blocks:
            return None
        
        try:
            builder = Builder.from_test_type(test_type)
            report = TestReport.from_test_type(test_type)
            
            # Resolve CPF
            if blocks.cpf_block:
                report.set_owner_cpf(builder.resolve_cpf(blocks.cpf_block))
            else:
                report.set_owner_cpf("XXXXXXXXXXX")
            
            # Process question blocks
            if blocks.questions_blocks:
                for block in blocks.questions_blocks:
                    report.update_answers(builder.resolve_question_block(block))
            
            return report
        except Exception as e:
            print(f"Error building report: {e}")
            return None
    
    def _draw_detections(self, core_image: CoreImage) -> np.ndarray:
        """Draw detection boxes on the image"""
        img = core_image.raw.copy()
        
        # Draw first stage detections
        if core_image.detections:
            for det in core_image.detections:
                bbox = det.to_pixels()
                color = (0, 255, 0)  # Green for first stage
                cv2.rectangle(
                    img,
                    (bbox.p_min.x, bbox.p_min.y),
                    (bbox.p_max.x, bbox.p_max.y),
                    color,
                    2
                )
                # Add label
                label = f"{det.model_assing_id}: {det.score:.2f}"
                cv2.putText(
                    img, label,
                    (bbox.p_min.x, bbox.p_min.y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1
                )
        
        # Draw second stage detections (from crops)
        for crop in core_image.crops:
            if crop.detections:
                for det in crop.detections:
                    # Convert to global coordinates
                    global_bbox = det.to_global_pixels()
                    color = (255, 0, 0)  # Blue for second stage
                    cv2.rectangle(
                        img,
                        (global_bbox.p_min.x, global_bbox.p_min.y),
                        (global_bbox.p_max.x, global_bbox.p_max.y),
                        color,
                        1
                    )
        
        return img
    
    def _collect_detections_info(
        self,
        core_image: CoreImage,
        fs_model: DetectionModel,
        ss_model: DetectionModel
    ) -> List[Dict[str, Any]]:
        """Collect detection information for API response"""
        detections = []
        
        # First stage detections
        if core_image.detections:
            for det in core_image.detections:
                bbox = det.to_pixels()
                class_name = fs_model.label_map.detections[det.model_assing_id].name if fs_model.label_map else str(det.model_assing_id)
                detections.append({
                    "stage": "first",
                    "class_id": det.model_assing_id,
                    "class_name": class_name,
                    "confidence": det.score,
                    "bbox": {
                        "x1": bbox.p_min.x,
                        "y1": bbox.p_min.y,
                        "x2": bbox.p_max.x,
                        "y2": bbox.p_max.y
                    }
                })
        
        # Second stage detections
        for crop in core_image.crops:
            if crop.detections:
                for det in crop.detections:
                    global_bbox = det.to_global_pixels()
                    class_name = ss_model.label_map.detections[det.model_assing_id].name if ss_model.label_map else str(det.model_assing_id)
                    detections.append({
                        "stage": "second",
                        "class_id": det.model_assing_id,
                        "class_name": class_name,
                        "confidence": det.score,
                        "bbox": {
                            "x1": global_bbox.p_min.x,
                            "y1": global_bbox.p_min.y,
                            "x2": global_bbox.p_max.x,
                            "y2": global_bbox.p_max.y
                        }
                    })
        
        return detections
    
    def export_to_csv(self, reports: List[Dict[str, Any]]) -> str:
        """Export reports to CSV format"""
        output = io.StringIO()
        
        if not reports:
            return ""
        
        # Get all question numbers from first report to determine columns
        first_report = reports[0]["report"]
        questions = first_report.get("questions", [])
        
        # Create header
        fieldnames = ["filename", "cpf"]
        for q in questions:
            fieldnames.append(f"Q{q['number']}")
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write rows
        for report_data in reports:
            row = {
                "filename": report_data["filename"],
                "cpf": report_data["report"].get("owner_cpf", "")
            }
            for q in report_data["report"].get("questions", []):
                row[f"Q{q['number']}"] = q.get("answer", "")
            writer.writerow(row)
        
        return output.getvalue()
