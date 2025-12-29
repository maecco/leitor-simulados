from __future__ import annotations

from core.image import CoreImage
from core.definitions.blocks import TestBlocks
from core.detection import DetectionContainer
from api.data_structs import ImageCacheStruct


class Cache:
    """
    A cache engine for storing image-related data in memory.

    Attributes
    ----------
    __data : list[ImageCacheStruct | None]
        A list storing cached image data or None if not yet cached.
    """

    def __init__(self, number_of_images: int):
        """
        Initializes the cache with a given number of image slots.

        Parameters
        ----------
        number_of_images : int
            The number of images to be cached.
        """
        self.__data: list[ImageCacheStruct | None] = [None] * number_of_images

    def cache_image(self, index: int, image: CoreImage):
        """
        Constructs the data structures for the given image and stores them in the cache at the specified index.

        Parameters
        ----------
        index : int
            The index in the cache where the image data will be stored.
        image : CoreImage
            The image to be cached.
        """
        detections = image.detections
        if not detections:
            return

        # Gather all detections, including those in cropped regions
        for crop in image.crops:
            detections.extend(crop.detections)
        container = DetectionContainer(detections)

        # Build blocks structure
        blocks: TestBlocks = image.to_block()

        # Save the structured data in cache
        self.__data[index] = ImageCacheStruct(
            image.name,
            container,
            blocks,
            report=None,
        )

    def from_index(self, index: int) -> ImageCacheStruct | None:
        """
        Retrieves the cached data at the given index.

        Parameters
        ----------
        index : int
            The index in the cache.

        Returns
        -------
        ImageCacheStruct | None
            The cached image data if available, otherwise None.
        """
        return self.__data[index]

    def get_all(self) -> list[ImageCacheStruct | None]:
        """
        Retrieves all cached image data.

        Returns
        -------
        list[ImageCacheStruct | None]
            A list of all cached image data, where each entry may be None if not yet cached.
        """
        return self.__data
