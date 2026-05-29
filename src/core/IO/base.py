from __future__ import annotations

import io
import pickle
from abc import ABC, abstractmethod

from utils.log import LoggingSystem

from .drivers import StorageDriver

class IOChannel(ABC):

    _io_drivers : list[StorageDriver] = list()

    def __init__(self):
        pass

    @property
    @abstractmethod
    def extension(self):
        self.extension

    def save(self, *args, **kwargs):
        # retuns a stream of bytes
        buffer = io.BytesIO()

    def load(self, *args, **kwargs):
        pass


    @abstractmethod
    def serialize(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def deserialize(self, *args, **kwargs):
        pass



class PickleIO(IOChannel):

    _logger = LoggingSystem.get_new_logger(__name__)

    def __init__(self):
        super().__init__()
        self._extension = '.pkl'

    @property
    def extension(self):
        return self._extension

    def serialize(self, data) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, data: bytes):
        return pickle.loads(data)


class ExcelIO(IOChannel):

    def __init__(self):
        super().__init__()
        self._extension = '.xlsx'

    @property
    def extension(self):
        return self._extension

    def serialize(self, data) -> bytes:
        pass  # Implement Excel serialization logic here

    def deserialize(self, data: bytes):
        pass  # Implement Excel deserialization logic here


    



            
            