from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class Serializer(ABC):
    """Abstract base class for serializers."""
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object."""
        pass

class SerializationManager:
    """Manages the serialization and deserialization of objects."""
    def __init__(self, msgspec_serializer: Serializer, dill_serializer: Serializer):
        self.msgspec_serializer = msgspec_serializer
        self.dill_serializer = dill_serializer

    def serialize(self, obj: Any) -> tuple[bytes, str]:
        """Serialize an object and return the data and serializer type."""
        try:
            return self.msgspec_serializer.serialize(obj), "msgspec"
        except TypeError:
            return self.dill_serializer.serialize(obj), "dill"

    def deserialize(self, data: bytes, serializer_type: str) -> Any:
        """Deserialize data using the specified serializer."""
        if serializer_type == "msgspec":
            return self.msgspec_serializer.deserialize(data)
        elif serializer_type == "dill":
            return self.dill_serializer.deserialize(data)
        else:
            raise ValueError(f"Unknown serializer type: {serializer_type}")
