from typing import Any, Type

import dill
import msgspec

# Sentinel to indicate dill was used for serialization
DILL_SENTINEL = b"__OMNIQ_DILL__"


class SerializerError(Exception):
    """Custom exception for serialization errors."""


class DeserializationError(Exception):
    """Custom exception for deserialization errors."""


class DualSerializer:
    """
    A dual-strategy serializer that uses msgspec for performance and dill for compatibility.
    """

    def __init__(self) -> None:
        self._msgpack_encoder = msgspec.msgpack.Encoder()
        self._msgpack_decoder = msgspec.msgpack.Decoder(type=Any)

    def serialize(self, obj: Any) -> bytes:
        """Serializes an object. Prefers msgspec, falls back to dill."""
        try:
            return self._msgpack_encoder.encode(obj)
        except (TypeError, msgspec.EncodeError):
            try:
                return DILL_SENTINEL + dill.dumps(obj)
            except Exception as e:
                raise SerializerError(f"Failed to serialize with msgspec and dill: {e}") from e

    def deserialize(self, data: bytes, target_type: Type[Any] | None = None) -> Any:
        """Deserializes an object, automatically detecting the serialization format."""
        if data.startswith(DILL_SENTINEL):
            return dill.loads(data[len(DILL_SENTINEL) :])
        return msgspec.msgpack.decode(data, type=target_type or Any)


default_serializer = DualSerializer()