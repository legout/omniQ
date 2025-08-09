"""Dill-based serializer for OmniQ."""

from typing import Any
import dill

from .base import BaseSerializer, SerializationError, DeserializationError


class DillSerializer(BaseSerializer):
    """Serializer using dill for advanced object serialization.
    
    This serializer uses dill for serialization of complex Python objects
    that cannot be handled by msgspec. It's the fallback serializer in
    OmniQ's dual-serializer strategy.
    """
    
    def __init__(self):
        """Initialize the dill serializer."""
        # Configure dill settings for better compatibility
        dill.settings['recurse'] = True
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize a Python object to bytes using dill.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data
            
        Raises:
            SerializationError: If the object cannot be serialized by dill
        """
        try:
            return dill.dumps(obj)
        except Exception as e:
            raise SerializationError(f"Failed to serialize object with dill: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to a Python object using dill.
        
        Args:
            data: The serialized data as bytes
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If the data cannot be deserialized by dill
        """
        try:
            return dill.loads(data)
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize data with dill: {e}") from e
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if an object can be serialized by dill.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if the object can be serialized, False otherwise
        """
        try:
            dill.dumps(obj)
            return True
        except Exception:
            return False