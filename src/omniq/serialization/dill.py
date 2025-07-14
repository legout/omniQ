from __future__ import annotations
from typing import Any
import dill
from .base import Serializer

class DillSerializer(Serializer):
    """Serializer using dill for complex Python objects."""
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes using dill."""
        return dill.dumps(obj)

    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object using dill."""
        return dill.loads(data)
