from typing import Any, TypeVar
from .detector import SerializationDetector
from .msgspec_serializer import MsgspecSerializer
from .dill_serializer import DillSerializer

T = TypeVar("T")

class SerializationManager:
    """Manages serialization strategy by selecting the appropriate serializer based on object compatibility."""
    
    def __init__(self, secret_key: bytes | None = None):
        """
        Initializes the SerializationManager with serializers and a detector.
        
        Args:
            secret_key: Optional bytes key for HMAC signature in DillSerializer.
        """
        self.detector = SerializationDetector()
        self.msgspec_serializer = MsgspecSerializer()
        self.dill_serializer = DillSerializer(secret_key=secret_key)
        self.format_metadata_key = "__serialization_format__"
    
    def serialize(self, obj: Any) -> dict[str, bytes]:
        """
        Serializes an object using the appropriate serializer and includes format metadata.
        
        Args:
            obj: The object to serialize.
            
        Returns:
            dict[str, bytes]: A dictionary containing the serialized data and format metadata.
        """
        serializer_name = self.detector.detect_serializer(obj)
        if serializer_name == 'msgspec':
            serialized_data = self.msgspec_serializer.serialize(obj)
        else:
            serialized_data = self.dill_serializer.serialize(obj)
            
        return {
            self.format_metadata_key: serializer_name.encode('utf-8'),
            "data": serialized_data
        }
    
    def deserialize(self, serialized_data: dict[str, bytes], type_hint: type[T] | None = None) -> T:
        """
        Deserializes data using the appropriate serializer based on stored format metadata.
        
        Args:
            serialized_data: A dictionary containing the serialized data and format metadata.
            type_hint: Optional type hint for deserialization.
            
        Returns:
            The deserialized object.
            
        Raises:
            KeyError: If format metadata is missing.
            ValueError: If the serializer format is unknown.
        """
        serializer_name = serialized_data[self.format_metadata_key].decode('utf-8')
        data = serialized_data["data"]
        
        if serializer_name == 'msgspec':
            return self.msgspec_serializer.deserialize(data, type_hint)
        elif serializer_name == 'dill':
            return self.dill_serializer.deserialize(data, type_hint)
        else:
            raise ValueError(f"Unknown serialization format: {serializer_name}")
