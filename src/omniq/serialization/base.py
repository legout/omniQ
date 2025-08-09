"""Base serialization interface for OmniQ."""

from abc import ABC, abstractmethod
from typing import Any, Union


class BaseSerializer(ABC):
    """Abstract base class for serializers.
    
    All serializers must implement serialize and deserialize methods
    to handle conversion between Python objects and serialized data.
    """
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize a Python object to bytes.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data
            
        Raises:
            SerializationError: If the object cannot be serialized
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to a Python object.
        
        Args:
            data: The serialized data as bytes
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If the data cannot be deserialized
        """
        pass


class SerializationError(Exception):
    """Raised when serialization fails."""
    pass


class DeserializationError(Exception):
    """Raised when deserialization fails."""
    pass