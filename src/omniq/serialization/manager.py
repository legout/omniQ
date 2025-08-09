"""Serialization manager implementing dual-serializer strategy for OmniQ."""

from typing import Any, Literal
import struct

from .base import BaseSerializer, SerializationError, DeserializationError
from .msgspec import MsgspecSerializer
from .dill import DillSerializer


# Serializer type identifiers (1 byte each)
MSGSPEC_IDENTIFIER = b'\x01'
DILL_IDENTIFIER = b'\x02'

SerializerType = Literal['msgspec', 'dill']


class SerializationManager:
    """Manages dual-serializer strategy for OmniQ.
    
    This manager implements the dual-serializer strategy:
    1. Attempts to serialize with msgspec first (high performance)
    2. Falls back to dill if msgspec fails (broader compatibility)
    3. Includes serializer identifier in the serialized data for proper deserialization
    """
    
    def __init__(self):
        """Initialize the serialization manager with both serializers."""
        self._msgspec_serializer = MsgspecSerializer()
        self._dill_serializer = DillSerializer()
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object using the dual-serializer strategy.
        
        First attempts to use msgspec for high performance. If that fails,
        falls back to dill for broader compatibility. The serialized data
        includes an identifier to indicate which serializer was used.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data with serializer identifier
            
        Raises:
            SerializationError: If both serializers fail
        """
        # Try msgspec first
        try:
            serialized_data = self._msgspec_serializer.serialize(obj)
            return MSGSPEC_IDENTIFIER + serialized_data
        except SerializationError:
            pass
        
        # Fall back to dill
        try:
            serialized_data = self._dill_serializer.serialize(obj)
            return DILL_IDENTIFIER + serialized_data
        except SerializationError as e:
            raise SerializationError(f"Both msgspec and dill serializers failed: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize data using the appropriate serializer.
        
        Reads the serializer identifier from the data and uses the
        corresponding serializer for deserialization.
        
        Args:
            data: The serialized data with serializer identifier
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If deserialization fails or identifier is invalid
        """
        if len(data) < 1:
            raise DeserializationError("Serialized data is too short to contain identifier")
        
        identifier = data[:1]
        serialized_data = data[1:]
        
        if identifier == MSGSPEC_IDENTIFIER:
            return self._msgspec_serializer.deserialize(serialized_data)
        elif identifier == DILL_IDENTIFIER:
            return self._dill_serializer.deserialize(serialized_data)
        else:
            raise DeserializationError(f"Unknown serializer identifier: {identifier}")
    
    def get_serializer_type(self, data: bytes) -> SerializerType:
        """Get the serializer type used for the given data.
        
        Args:
            data: The serialized data with serializer identifier
            
        Returns:
            SerializerType: The type of serializer used ('msgspec' or 'dill')
            
        Raises:
            DeserializationError: If identifier is invalid
        """
        if len(data) < 1:
            raise DeserializationError("Serialized data is too short to contain identifier")
        
        identifier = data[:1]
        
        if identifier == MSGSPEC_IDENTIFIER:
            return 'msgspec'
        elif identifier == DILL_IDENTIFIER:
            return 'dill'
        else:
            raise DeserializationError(f"Unknown serializer identifier: {identifier}")
    
    def can_serialize_with_msgspec(self, obj: Any) -> bool:
        """Check if an object can be serialized with msgspec.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if msgspec can serialize the object, False otherwise
        """
        return self._msgspec_serializer.can_serialize(obj)
    
    def can_serialize_with_dill(self, obj: Any) -> bool:
        """Check if an object can be serialized with dill.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if dill can serialize the object, False otherwise
        """
        return self._dill_serializer.can_serialize(obj)
    
    def force_serialize_with_msgspec(self, obj: Any) -> bytes:
        """Force serialization with msgspec only.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data with msgspec identifier
            
        Raises:
            SerializationError: If msgspec serialization fails
        """
        serialized_data = self._msgspec_serializer.serialize(obj)
        return MSGSPEC_IDENTIFIER + serialized_data
    
    def force_serialize_with_dill(self, obj: Any) -> bytes:
        """Force serialization with dill only.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data with dill identifier
            
        Raises:
            SerializationError: If dill serialization fails
        """
        serialized_data = self._dill_serializer.serialize(obj)
        return DILL_IDENTIFIER + serialized_data