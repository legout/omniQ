# src/omniq/serialization/manager.py
"""Serialization manager for OmniQ."""

from typing import Any

from omniq.serialization.msgspec import MsgspecSerializer
from omniq.serialization.dill import DillSerializer

class SerializationManager:
    """Manager for serialization."""
    
    def __init__(self):
        """Initialize the serialization manager."""
        self.msgspec_serializer = MsgspecSerializer()
        self.dill_serializer = DillSerializer()
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        # Try msgspec first
        if self.msgspec_serializer.can_serialize(obj):
            serialized = self.msgspec_serializer.serialize(obj)
            # Add format prefix
            return b"msgspec:" + serialized
        
        # Fall back to dill
        serialized = self.dill_serializer.serialize(obj)
        return b"dill:" + serialized
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object."""
        # Check format prefix
        if data.startswith(b"msgspec:"):
            return self.msgspec_serializer.deserialize(data[8:])
        elif data.startswith(b"dill:"):
            return self.dill_serializer.deserialize(data[5:])
        
        # No prefix, try to guess
        try:
            return self.msgspec_serializer.deserialize(data)
        except Exception:
            return self.dill_serializer.deserialize(data)