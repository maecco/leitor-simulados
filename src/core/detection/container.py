from __future__ import annotations
from .base import Detection


class DetectionContainer:
    
    def __init__(self, detections: list[Detection] | None = None) -> None:
        self._detections: list[Detection] = detections if detections is not None else []
        self._by_type: dict[Detection.Type, list[Detection]] = {}
        self._build_by_type()

    def add_detection(self, detection: Detection) -> None:
        self._detections.append(detection)
        if detection.class_type not in self._by_type:
            self._by_type[detection.class_type] = []
        self._by_type[detection.class_type].append(detection)

    def set_detections(self, detections: list[Detection]) -> None:
        self._detections = detections
        self._build_by_type()

    def get_detections(self) -> list[Detection]:
        return self._detections

    def get_by_type(
            self,
            class_types: list[Detection.Type] | Detection.Type,
            to_list: bool = False
        ) -> dict[Detection.Type, list[Detection]] | list[Detection]:
        if isinstance(class_types, Detection.Type):
            class_types = [class_types]
        if to_list:
            return [
                item for class_type in class_types
                if class_type in self._by_type
                for item in self._by_type[class_type]
            ]
        return {k: v for k, v in self._by_type.items() if k in class_types}

    def __len__(self) -> int:
        return len(self._detections)
    
    def __bool__(self) -> bool:
        return len(self._detections) > 0

    def _build_by_type(self) -> None:
        self._by_type = {}
        for detection in self._detections:
            if detection.class_type not in self._by_type:
                self._by_type[detection.class_type] = []
            self._by_type[detection.class_type].append(detection)
