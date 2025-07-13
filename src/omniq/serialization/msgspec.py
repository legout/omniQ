"""MsgspecSerializer for high-performance serialization of compatible types."""

from __future__ import annotations

from typing import Any

import msgspec

from .base import BaseSerializer, SerializationDetector


class MsgspecSerializer(BaseSerializer):
    """High-performance serializer using msgspec for compatible types."""
    
    def __init__(self, strict: bool = True):
        """
        Initialize msgspec serializer.
        
        Args:
            strict: If True, use strict mode for better performance
        """
        self.strict = strict
        self._encoder = msgspec.msgpack.Encoder()
        self._decoder = msgspec.msgpack.Decoder()
    
    @property
    def name(self) -> str:
        """Serializer name."""
        return "msgspec"
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if msgspec can serialize this object."""
        return SerializationDetector.is_msgspec_compatible(obj)
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize object using msgspec."""
        try:
            return self._encoder.encode(obj)
        except Exception as e:
            raise ValueError(f"Failed to serialize with msgspec: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes using msgspec."""
        try:
            return self._decoder.decode(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize with msgspec: {e}") from e