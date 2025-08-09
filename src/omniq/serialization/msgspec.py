"""Msgspec-based serializer for OmniQ."""

from typing import Any
import msgspec

from .base import BaseSerializer, SerializationError, DeserializationError


class MsgspecSerializer(BaseSerializer):
    """Serializer using msgspec for high-performance serialization.
    
    This serializer uses msgspec for fast serialization of compatible types.
    It's the primary serializer in OmniQ's dual-serializer strategy.
    """
    
    def __init__(self):
        """Initialize the msgspec serializer."""
        self._encoder = msgspec.msgpack.Encoder()
        self._decoder = msgspec.msgpack.Decoder()
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize a Python object to bytes using msgspec.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data
            
        Raises:
            SerializationError: If the object cannot be serialized by msgspec
        """
        try:
            return self._encoder.encode(obj)
        except (TypeError, ValueError, msgspec.EncodeError) as e:
            raise SerializationError(f"Failed to serialize object with msgspec: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to a Python object using msgspec.
        
        Args:
            data: The serialized data as bytes
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If the data cannot be deserialized by msgspec
        """
        try:
            return self._decoder.decode(data)
        except (ValueError, msgspec.DecodeError) as e:
            raise DeserializationError(f"Failed to deserialize data with msgspec: {e}") from e
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if an object can be serialized by msgspec.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if the object can be serialized, False otherwise
        """
        try:
            self._encoder.encode(obj)
            return True
        except (TypeError, ValueError, msgspec.EncodeError):
            return False