from __future__ import annotations
from typing import Any
import msgspec
from .base import Serializer

class MsgspecSerializer(Serializer):
    """Serializer using msgspec for high-performance serialization."""
    def __init__(self):
        self.encoder = msgspec.msgpack.Encoder()
        self.decoder = msgspec.msgpack.Decoder()

    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes using msgspec."""
        return self.encoder.encode(obj)

    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to an object using msgspec."""
        return self.decoder.decode(data)
