# src/omniq/serialization/dill.py
"""Dill serializer for OmniQ."""

import dill
from typing import Any

from omniq.serialization.base import Serializer

class DillSerializer(Serializer):
    """Serializer using dill."""
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes."""
        return dill.dumps(obj)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object."""
        return dill.loads(data)