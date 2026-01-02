from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from core.definitions.enums import ModelType, TestType, Stage
from core.definitions.geometry import FloatBoundingBox
from core.image import CoreImage
from core.detection.base import Detection
from core.IO import MODELS_PATH
from core.IO.base import Importer
from core.detection.label_map import (
    LabelMap,
    DEFAULT_FIRST_STAGE_LABEL_MAP,
    DEFAULT_SECOND_STAGE_LABEL_MAP
)



# SECTION: Model enum and base class

class DetectionModel(ABC):

    @classmethod
    def from_models_path(
        cls,
        rel_path : str,
        stage : Stage = Stage.NULL,
        test : TestType = TestType.NULL,
        device : str = "auto"
        ) -> DetectionModel:
        """
        Load the model from the models path
        
        Args:
            rel_path: Relative path to model file
            stage: Processing stage (FIRST, SECOND, BOTH)
            test: Test type for EFScanAlgo models
            device: Device for YOLO models ("auto", "cpu", "cuda", etc.)
        """

        # Get the model label map
        model_path : Path = MODELS_PATH / rel_path
        label_maps : dict = Importer.JSON.load_label_maps()
        if label_maps:
            key = rel_path.replace('\\', '/')
            label_map = LabelMap.from_json(label_maps.get(key))
        else:
            label_map = None
        if not label_map:
            if stage == Stage.FIRST:
                label_map = DEFAULT_FIRST_STAGE_LABEL_MAP
            elif stage == Stage.SECOND:
                label_map = DEFAULT_SECOND_STAGE_LABEL_MAP
        
        # Get the model type
        parts = model_path.parts
        model_name = parts[-1]
        
        # Get the type of the model and load accordingly
        model_suffix = model_name.split('.')[-1]
        
        # EFScanAlgo model
        if model_suffix == 'py':
            return EFScanAlgoModel(model_name, stage, test, label_map)
        
        # YOLOV8 model
        elif model_suffix == 'pt':
            engine = YOLO(model_path)
            return YOLOModel(engine, label_map, device=device)


    def __init__(
            self,
            model_type : ModelType,
            target_stage : Stage = Stage.NULL,
            label_map : LabelMap = None
        ):
        self.model_type = model_type
        self.target_stage = target_stage
        self.label_map = label_map

    @abstractmethod
    def detect(self, img : CoreImage) -> list[Detection]:
        pass        



# SECTION: Model classes



# SECTION: YOLOV8 MODEL


class YOLOModel(DetectionModel):
    def __init__(self, engine : YOLO, label_map : LabelMap, device: str = "auto"):
        super().__init__(ModelType.YOLOV8, label_map=label_map)
        self.engine = engine
        self.device = self._resolve_device(device)
    
    def _resolve_device(self, device: str) -> str:
        """Resolve the device to use for inference"""
        if device == "auto":
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
    
    def get_device_info(self) -> dict:
        """Get information about the device being used"""
        import torch
        info = {
            "device": self.device,
            "cuda_available": torch.cuda.is_available(),
        }
        if torch.cuda.is_available():
            info["cuda_device_count"] = torch.cuda.device_count()
            info["cuda_device_name"] = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None
        return info

    def detect(self, img : CoreImage) -> list[Detection]:
        result = self.engine.predict(img.raw, verbose=False, device=self.device)[0]
        detections = []
        boxes = result.boxes.xyxyn.tolist()
        classes = result.boxes.cls.tolist()
        confs = result.boxes.conf.tolist()
        for box, class_id, conf in zip(boxes, classes, confs):
            box = FloatBoundingBox.from_floats(*box)
            detections.append(
                Detection(
                    box,
                    int(class_id),
                    float(conf),
                    img.raw.shape[1],
                    img.raw.shape[0],
                )
            )
        return detections



# SECTION: EFSCANALGO MODEL (NO AI)


class EFScanAlgoModel(DetectionModel):
    
    __initialized = False
    __scanner = None
    def __init__(self, name : str, stage : Stage, test : TestType, label_map : LabelMap):
        super().__init__(ModelType.EFSCANALGO, label_map=label_map)
        
        # Set path to import dynamically
        if not self.__initialized:
            self.__init_paths()
        
        # Import the relevant classes to initialize the model
        from EFScanAlgoCore import Scanner
        
        # Initialize static variables
        self.name = name
        self.stage = stage
        self.test = test
        
        # Import the relevant classes to initialize the model
        self.__scanner = Scanner(
            self.name,
            self.test,
            self.stage
        )


    ## Detection function ##

    def detect(self, img : CoreImage) -> list[Detection]:
        return self.__scanner.detect(img)
        

    # Auxiliar initialization function
    
    def __init_paths(self):
        
        # Include the path to the sys tracked directories
        # ../leinor-simulados/models
        # Include path to models EFscanAlgo
        import sys
        if not MODELS_PATH in sys.path:
            sys.path.append(str(MODELS_PATH.resolve()))
        self.__initialized = True