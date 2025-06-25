# src/omniq/serialization/msgspec.py
"""MsgSpec serializer for OmniQ."""

import msgspec
from typing import Any

from omniq.serialization.base import Serializer

class MsgspecSerializer(Serializer):
    """Serializer using msgspec."""
    
    def __init__(self):
        """Initialize the serializer."""
        self.encoder = msgspec.json.Encoder()
        self.decoder = msgspec.json.Decoder()
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        return self.encoder.encode(obj)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object."""
        return self.decoder.decode(data)
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if the object type is supported by msgspec."""
        # msgspec supports basic types: dict, list, tuple, str, int, float, bool, None
        # and dataclasses/attrs/pydantic models if configured, but here we check for basic types
        supported_types = (dict, list, tuple, str, int, float, bool, type(None))
        if isinstance(obj, supported_types):
            return True
        else:
            try:
                # Try to serialize using msgspec to see if it raises an error
                self.serialize(obj)
                return True
            except (msgspec.EncodeError, TypeError):
                return False
           
