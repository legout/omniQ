"""Dill-based serializer for OmniQ."""

from typing import Any, List, Optional
import dill
import logging
import inspect
import traceback

from .base import BaseSerializer, SerializationError, DeserializationError


class DillSerializer(BaseSerializer):
    """Serializer using dill for advanced object serialization.
    
    This serializer uses dill for serialization of complex Python objects
    that cannot be handled by msgspec. It's the fallback serializer in
    OmniQ's dual-serializer strategy.
    """
    
    def __init__(self):
        """Initialize the dill serializer."""
        # Configure dill settings for better compatibility
        dill.settings['recurse'] = True
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize a Python object to bytes using dill.
        
        Args:
            obj: The Python object to serialize
            
        Returns:
            bytes: The serialized data
            
        Raises:
            SerializationError: If the object cannot be serialized by dill
        """
        try:
            return dill.dumps(obj)
        except dill.PicklingError as e:
            logging.error(f"Dill pickling error: {traceback.format_exc()}")
            raise SerializationError(f"Failed to serialize object with dill: {e}") from e
        except Exception as e:
            logging.error(f"Unexpected serialization error: {traceback.format_exc()}")
            raise SerializationError(f"Failed to serialize object with dill: {e}") from e
    
    def safe_deserialize(self, data: bytes, allowed_modules: Optional[List[str]] = None) -> Any:
        """Safely deserialize bytes back to a Python object using dill with module validation.
        
        Args:
            data: The serialized data as bytes
            allowed_modules: Optional list of allowed module names for validation
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If the data cannot be deserialized by dill or module validation fails
        """
        if allowed_modules is None:
            logging.warning("Deserializing with dill without module restrictions - this may be unsafe")
        
        try:
            obj = dill.loads(data)
            
            # Validate modules if allowed_modules is provided
            if allowed_modules is not None:
                self._validate_object_modules(obj, allowed_modules)
            
            return obj
        except dill.UnpicklingError as e:
            logging.error(f"Dill unpickling error: {traceback.format_exc()}")
            raise DeserializationError(f"Failed to deserialize data with dill: {e}") from e
        except Exception as e:
            logging.error(f"Unexpected deserialization error: {traceback.format_exc()}")
            raise DeserializationError(f"Failed to deserialize data with dill: {e}") from e
    
    def _validate_object_modules(self, obj: Any, allowed_modules: List[str]) -> None:
        """Validate that all modules in the object are in the allowed list.
        
        Args:
            obj: The object to validate
            allowed_modules: List of allowed module names
            
        Raises:
            DeserializationError: If any module is not in the allowed list
        """
        # Check if the object is a callable/function
        if callable(obj):
            module = inspect.getmodule(obj)
            if module is not None and module.__name__ not in allowed_modules:
                raise DeserializationError(
                    f"Module '{module.__name__}' is not in the allowed modules list: {allowed_modules}"
                )
        
        # Check if the object is a class
        elif inspect.isclass(obj):
            module = inspect.getmodule(obj)
            if module is not None and module.__name__ not in allowed_modules:
                raise DeserializationError(
                    f"Module '{module.__name__}' is not in the allowed modules list: {allowed_modules}"
                )
        
        # Check if the object is an instance with a class
        elif hasattr(obj, '__class__'):
            module = inspect.getmodule(obj.__class__)
            if module is not None and module.__name__ not in allowed_modules:
                raise DeserializationError(
                    f"Module '{module.__name__}' is not in the allowed modules list: {allowed_modules}"
                )
        
        # Recursively check collections (list, tuple, dict, set)
        elif isinstance(obj, (list, tuple, set)):
            for item in obj:
                self._validate_object_modules(item, allowed_modules)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                self._validate_object_modules(key, allowed_modules)
                self._validate_object_modules(value, allowed_modules)
    
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to a Python object using dill.
        
        Args:
            data: The serialized data as bytes
            
        Returns:
            Any: The deserialized Python object
            
        Raises:
            DeserializationError: If the data cannot be deserialized by dill
        """
        return self.safe_deserialize(data, allowed_modules=None)
    
    def can_serialize(self, obj: Any) -> bool:
        """Check if an object can be serialized by dill.
        
        Args:
            obj: The object to check
            
        Returns:
            bool: True if the object can be serialized, False otherwise
        """
        try:
            dill.dumps(obj)
            return True
        except Exception:
            return False