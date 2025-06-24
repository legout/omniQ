import msgspec
from typing import Any, TypeVar

T = TypeVar("T")

class MsgspecSerializer:
    """Serializer using msgspec for high-performance serialization of compatible types."""
    
    def __init__(self):
        self.encoder = msgspec.json.Encoder()
        self.decoder = msgspec.json.Decoder()
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serializes an object to bytes using msgspec.
        
        Args:
            obj: The object to serialize.
            
        Returns:
            bytes: The serialized data.
            
        Raises:
            msgspec.EncodeError: If serialization fails.
        """
        return self.encoder.encode(obj)
    
    def deserialize(self, data: bytes, type_hint: type[T] | None = None) -> T:
        """
        Deserializes bytes to an object using msgspec.
        
        Args:
            data: The bytes data to deserialize.
            type_hint: Optional type hint for deserialization.
            
        Returns:
            The deserialized object.
            
        Raises:
            msgspec.DecodeError: If deserialization fails.
        """
        if type_hint:
            decoder = msgspec.json.Decoder(type=type_hint)
            return decoder.decode(data)
        return self.decoder.decode(data)
