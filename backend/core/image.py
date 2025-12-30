# for Image.get_cropped type hinting
from __future__ import annotations
from typing import Generator
from pathlib import Path
from functools import wraps

import cv2
import numpy as np

from core.definitions.blocks import TestBlocks, Block
from core.definitions.geometry import IntPoint
from core.detection import Detection, DetectionContainer

from utils.memory import MemoryTracker, MemoryCategory



class CoreImage():
    """
    CoreImage class is used to represent an image with its detections and cropped subregions.

    Attributes:
    - raw: The raw image data.
    - name: The name of the image as in the file.
    - detections: A list of detections in the image.
    - height: The height of the image.
    - width: The width of the image.
    - crops: A list of cropped subregions of the image.
    - cropped_from: The image that this image was cropped from.
    - cropped_from_detection: The type of detection that this image was cropped from.
    - anchored_at: The point where the image was cropped from the original image.
    - order: The order of the image in the cropped image list.
    - BOUNDING_BOXES_DRAWN: A flag that indicates if the bounding boxes were drawn in the image.
    """
    
    @classmethod
    def from_paths(
            cls,
            paths: list[str],
            lazy: bool = True
        ) -> Generator[CoreImage, None, None] | list[CoreImage]:
        """
        Constructor that creates CoreImage objects from a list of file paths.

        Parameters:
        - paths : list[str]
            A list of file paths.
        - lazy : bool
            If True, returns a generator (lazy loading).
            If False, returns a list (eager loading).
        
        Returns:
        - Generator[CoreImage] if lazy=True
        - list[CoreImage] if lazy=False
        """
        if not lazy:
            return [cls.from_path(path) for path in paths]
        
        def _lazy_generator():
            for path in paths:
                yield cls.from_path(path)
        
        return _lazy_generator()

    @classmethod
    def from_path(cls, path: str) -> CoreImage:
        """
        Constructor that creates a CoreImage object from a file path.
        
        Parameters:
        - path : str
            The file path to the image.
        
        Returns:
        - CoreImage: The loaded image object.
        """
        path_obj = Path(path)
        name: str = path_obj.name
        raw: np.ndarray = cv2.imread(str(path_obj))
        detections: list[Detection] | None = None
        return cls(name, raw, detections, _source_path=path)
    

    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (0,255,255), (255,0,255), (0,0,0)]

    def __init__(
            self,
            name,
            raw,
            detections,
            cropped_from = None,
            cropped_from_detection=None,
            anchored_at : IntPoint | None = None,
            order : int = -1,
            _source_path : str = None
            ) -> None:
        self.raw : np.ndarray = raw
        self.name : str = name
        self.detections : list[Detection] = detections
        self.height : int = raw.shape[0]
        self.width : int = raw.shape[1]
        self.crops : list[CoreImage] = []
        # Those variable are for the cropped images
        self.cropped_from : CoreImage = cropped_from
        self.cropped_from_detection : Detection = cropped_from_detection
        self.anchored_at : IntPoint = anchored_at
        self.order : int = order
        
        # Track memory allocation
        category = MemoryCategory.CORE_IMAGE_CROP if cropped_from else MemoryCategory.CORE_IMAGE
        source = _source_path or f"crop_from:{cropped_from.name if cropped_from else 'unknown'}"
        MemoryTracker.track_allocation(
            self.raw, 
            category, 
            source=f"CoreImage.__init__",
            description=f"{name} ({self.width}x{self.height})"
        )

    
    ## Aux decoration functions ##

    @staticmethod
    def _has_detections(func):
        """Decorator that ensures detections are set before calling the method."""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.detections is None:
                raise ValueError("CoreImage detections not set")
            return func(self, *args, **kwargs)
        return wrapper
    

    ## Detection functions ##

    def make_detections_with_model(self, model, score_threshold) -> None:
        detections = model.detect(self)
        # Filter detections by score
        self.detections = [d for d in detections if d.score > score_threshold]
        # If the image is a crop, then add the ancor point to the detections
        # as the point where the crop was made
        if self.anchored_at:
            for detection in self.detections:
                detection.anchored_at = self.anchored_at
                detection.parent_image = self
                # TODO: Change this to a set function
                detection.global_pixel_bounding_box = detection.to_global_pixels()
        else:
            for detection in self.detections:
                detection.global_pixel_bounding_box = detection.to_pixels()
        # sort and mark detections from top left to bottom right    
        self.detections.sort()

        for i, detection in enumerate(self.detections):
            detection.order = i
        self.BOUNDING_BOXES_DRAWN = False
    
    @_has_detections
    def make_cropped(self) -> bool:
        """
        Creates cropped sub-images from detections.
        
        Returns:
            bool: True if crops were created successfully, False if no detections.
        """
        if not self.detections:
            return False
        cropped = []
        # the detections are sorted by top left to bottom right
        cont = 1
        current_class = self.detections[0].class_type
        for detection in self.detections:
            if detection.class_type != current_class:
                cont = 1
                current_class = detection.class_type
            xmin, ymin, xmax, ymax = detection.to_pixels()
            cropped.append(
                CoreImage(
                    f"{self.name.split('.')[0]}_{detection.class_type.name.lower()}_{cont:02}.jpg",
                    self.raw[ymin:ymax, xmin:xmax],
                    None,
                    cropped_from = self,
                    cropped_from_detection = detection,
                    anchored_at = IntPoint(xmin, ymin),
                    order = cont
                )
            )
            cont += 1
        self.crops = cropped
        return True
            

    ## Exporting functions ##
    
    def to_json(self, only_ball_detections=True) -> list:
        if only_ball_detections:
            json_data = []
            for detection in self.detections:
                if 'ball' in detection.class_name:
                    json_data.append(detection.to_json())
            return json_data
        else:
            json_data = []
            if self.detections:
                for detection in self.detections:
                    json_data.append(detection.to_json())
            return json_data
    
    def to_yolo(self) -> str:
        yolo = '\n'.join([detection.to_yolo() for detection in self.detections])
        return yolo
    
    def to_block(self) -> TestBlocks | Block:
        # Check if is the root image
        # if not return a block
        if self.cropped_from:
            return Block(
                root_detection = self.cropped_from_detection,
                order = self.order,
                container = DetectionContainer(self.detections)
            )
        # else create a TestBlocks object
        cpf_block = None
        questions_blocks = []
        for crop in self.crops:
            block = crop.to_block()
            if block.root_detection.class_type == Detection.Type.CPF_BLOCK:
                cpf_block = block
            else:
                questions_blocks.append(block)
        questions_blocks.sort(key=lambda b: b.order)
        # Return the object
        return TestBlocks(
            name = self.name,
            cpf_block = cpf_block,
            questions_blocks = questions_blocks
        )
    
    ## Import function ##

    def import_blocks(self, blocks : TestBlocks | Block) -> None:
        
        # Case where is a root image
        if not self.cropped_from:
            if not isinstance(blocks, TestBlocks):
                raise Exception(
                    "Blocks must be a TestBlocks object for a root image"
                )
            
            # Get the first stage detections
            self.detections = [block.root_detection for block in blocks]
            
            # Make the cropped images
            self.make_cropped()

            # Sort the question blocks
            ordered_blocks = sorted(blocks.questions_blocks, key=lambda b: b.order)
            # Recursively call the function for the cropped images
            for crop in self.crops:
                if crop.cropped_from_detection.class_type == Detection.Type.CPF_BLOCK:
                    crop.import_blocks(blocks.cpf_block)
                else:
                    order = crop.order
                    crop.import_blocks(ordered_blocks[order - 1]) 
                    # -1 because the order starts at 1
        
        # Case where is a cropped image
        else:
            if not isinstance(blocks, Block):
                raise Exception(
                    "Blocks must be a Block object for a cropped image"
                )
            self.detections = blocks.container.get_detections()
                    

    ## Saving fuction ## 

    def save(self, path : Path) -> None:
        out_path = path / self.name     
        cv2.imwrite(str(out_path), self.raw)
    
    ## Memory management functions ##

    def free(self) -> None:
        """
        Recursively frees the memory used by this image and all its 
        cropped sub-images.

        This method breaks both parent-to-child (`crops`) and 
        child-to-parent (`cropped_from`) references to aid garbage collection.
        """
        for crop in self.crops:
            crop.free()
        
        # Track deallocation before clearing
        if self.raw is not None:
            MemoryTracker.track_deallocation(self.raw)
        
        self.raw = None
        self.detections = None

        self.crops = []
        self.cropped_from = None
