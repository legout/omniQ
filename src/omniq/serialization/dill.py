"""DillSerializer for complex Python objects that msgspec cannot handle."""

from __future__ import annotations

from typing import Any

import dill

from .base import BaseSerializer


class DillSerializer(BaseSerializer):
    """Fallback serializer using dill for complex Python objects."""
    
    def __init__(self, protocol: int = dill.HIGHEST_PROTOCOL):
        """
        Initialize dill serializer.
        
        Args:
            protocol: Pickle protocol version to use
        """
        self.protocol = protocol
    
    @property
    def name(self) -> str:
        """Serializer name."""
        return "dill"
    
    def can_serialize(self, obj: Any) -> bool:
        """Dill can serialize almost anything, so always return True."""
        return True
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize object using dill."""
        try:
            return dill.dumps(obj, protocol=self.protocol)
        except Exception as e:
            raise ValueError(f"Failed to serialize with dill: {e}") from e
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes using dill."""
        try:
            return dill.loads(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize with dill: {e}") from e