# src/omniq/serialization/base.py
"""Base serializer for OmniQ."""

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