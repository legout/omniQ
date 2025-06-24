from typing import Any, TypeVar

T = TypeVar("T")

class SerializationDetector:
    """Detects the compatibility of objects with different serializers."""
    
    def __init__(self):
        self.msgspec_compatible_types = (int, float, str, bool, list, dict, tuple, set)
    
    def is_msgspec_compatible(self, obj: Any) -> bool:
        """
        Determines if an object can be serialized using msgspec.
        
        Args:
            obj: The object to check for compatibility.
            
        Returns:
            bool: True if the object is compatible with msgspec, False otherwise.
        """
        # Basic type check for primitive types
        if isinstance(obj, self.msgspec_compatible_types):
            return True
            
        # Check for nested structures
        if isinstance(obj, (list, tuple, set)):
            return all(self.is_msgspec_compatible(item) for item in obj)
        elif isinstance(obj, dict):
            return all(
                isinstance(key, str) and self.is_msgspec_compatible(value)
                for key, value in obj.items()
            )
            
        # Check if the object is a msgspec Struct
        if hasattr(obj, "__struct_fields__"):
            return True
            
        return False
    
    def detect_serializer(self, obj: Any) -> str:
        """
        Detects the appropriate serializer for the given object.
        
        Args:
            obj: The object to detect the serializer for.
            
        Returns:
            str: The name of the serializer to use ('msgspec' or 'dill').
        """
        return 'msgspec' if self.is_msgspec_compatible(obj) else 'dill'
