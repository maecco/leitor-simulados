

from abc import ABC, abstractmethod
from typing import Any


# Base Serializer class

class Serializer(ABC):
    
    @abstractmethod
    def serialize(self, data) -> bytes:
        pass

    @abstractmethod
    def deserialize(self, data: bytes):
        pass


# Concrete Classes

# Pickle Serializer implementation


class PickleSerializer(Serializer):
    
    def serialize(self, data : ) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, data: bytes):
        return pickle.loads(data)