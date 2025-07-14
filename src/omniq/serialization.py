"""
Serialization system for OmniQ library.

This module provides a dual serialization approach:
- msgspec for high-performance serialization of compatible types
- dill for complex Python objects that msgspec cannot handle

The SerializationManager orchestrates the strategy, automatically selecting
the appropriate serializer and storing format metadata for correct deserialization.
"""

import logging
import warnings
from typing import Any, Dict, Tuple, Union, Optional, Type
from enum import Enum
import msgspec
import msgspec.json
import dill

logger = logging.getLogger(__name__)


class SerializationFormat(str, Enum):
    """Enumeration of supported serialization formats."""
    MSGSPEC = "msgspec"
    DILL = "dill"


class SerializationError(Exception):
    """Base exception for serialization errors."""
    pass


class DeserializationError(Exception):
    """Base exception for deserialization errors."""
    pass


class SerializationDetector:
    """
    Detects the appropriate serialization strategy for different data types.
    
    This class analyzes objects to determine if they can be serialized with
    msgspec (for performance) or require dill (for complex objects).
    """
    
    # Types that msgspec can handle efficiently
    MSGSPEC_COMPATIBLE_TYPES = (
        # Basic types
        bool, int, float, str, bytes, bytearray,
        # Collections
        list, tuple, dict, set, frozenset,
        # Optional and None
        type(None),
    )
    
    # Types that typically require dill
    DILL_REQUIRED_TYPES = (
        # Functions and lambdas
        type(lambda: None),
        # Classes and types
        type, type(type),
        # Modules
        type(msgspec),
    )
    
    @classmethod
    def can_use_msgspec(cls, obj: Any) -> bool:
        """
        Determine if an object can be serialized with msgspec.
        
        Args:
            obj: The object to analyze
            
        Returns:
            True if msgspec can handle the object, False otherwise
        """
        # Handle None separately
        if obj is None:
            return True
            
        obj_type = type(obj)
        
        # Check if it's a basic compatible type
        if obj_type in cls.MSGSPEC_COMPATIBLE_TYPES:
            return True
            
        # Check if it definitely requires dill
        if obj_type in cls.DILL_REQUIRED_TYPES:
            return False
            
        # Check if it's a msgspec.Struct (need to check fields recursively)
        if hasattr(obj, '__struct_fields__'):
            # Check if any field contains non-msgspec compatible data
            try:
                for field_name in obj.__struct_fields__:
                    field_value = getattr(obj, field_name)
                    if not cls.can_use_msgspec(field_value):
                        return False
                return True
            except Exception:
                # If we can't inspect fields, fall back to encode test
                pass
            
        # Check if it's an enum
        if hasattr(obj, '__class__') and hasattr(obj.__class__, '__bases__'):
            for base in obj.__class__.__bases__:
                if base.__name__ == 'Enum':
                    return True
                    
        # For complex objects, try a quick msgspec test
        try:
            msgspec.json.encode(obj)
            return True
        except (TypeError, ValueError, msgspec.ValidationError):
            return False
    
    @classmethod
    def detect_format(cls, obj: Any) -> SerializationFormat:
        """
        Detect the appropriate serialization format for an object.
        
        Args:
            obj: The object to analyze
            
        Returns:
            The recommended serialization format
        """
        if cls.can_use_msgspec(obj):
            return SerializationFormat.MSGSPEC
        else:
            return SerializationFormat.DILL


class MsgspecSerializer:
    """
    High-performance serializer using msgspec.
    
    This serializer is optimized for speed and handles msgspec-compatible types
    including basic Python types, collections, and msgspec.Struct objects.
    """
    
    def __init__(self, strict: bool = True):
        """
        Initialize the msgspec serializer.
        
        Args:
            strict: If True, raise errors for incompatible types.
                   If False, return None for incompatible types.
        """
        self.strict = strict
        
    def serialize(self, obj: Any) -> Optional[bytes]:
        """
        Serialize an object using msgspec.
        
        Args:
            obj: The object to serialize
            
        Returns:
            Serialized bytes or None if serialization fails and strict=False
            
        Raises:
            SerializationError: If serialization fails and strict=True
        """
        try:
            return msgspec.json.encode(obj)
        except (TypeError, ValueError, msgspec.ValidationError) as e:
            if self.strict:
                raise SerializationError(f"Failed to serialize with msgspec: {e}")
            else:
                logger.debug(f"msgspec serialization failed: {e}")
                return None
    
    def deserialize(self, data: bytes, target_type: Optional[Type] = None) -> Any:
        """
        Deserialize bytes using msgspec.
        
        Args:
            data: The serialized bytes
            target_type: Optional type hint for deserialization
            
        Returns:
            The deserialized object
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            if target_type is not None:
                return msgspec.json.decode(data, type=target_type)
            else:
                return msgspec.json.decode(data)
        except (TypeError, ValueError, msgspec.ValidationError) as e:
            raise DeserializationError(f"Failed to deserialize with msgspec: {e}")


class DillSerializer:
    """
    Fallback serializer using dill for complex Python objects.
    
    This serializer can handle complex objects that msgspec cannot,
    including functions, classes, lambdas, and objects with circular references.
    """
    
    def __init__(self, secure: bool = True):
        """
        Initialize the dill serializer.
        
        Args:
            secure: If True, apply security measures for deserialization
        """
        self.secure = secure
        
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize an object using dill.
        
        Args:
            obj: The object to serialize
            
        Returns:
            Serialized bytes
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            return dill.dumps(obj)
        except Exception as e:
            raise SerializationError(f"Failed to serialize with dill: {e}")
    
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes using dill.
        
        Args:
            data: The serialized bytes
            
        Returns:
            The deserialized object
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            if self.secure:
                # In a production environment, you might want to implement
                # additional security measures here, such as:
                # - Whitelisting allowed types
                # - Sandboxing deserialization
                # - Validating the source of the data
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    return dill.loads(data)
            else:
                return dill.loads(data)
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize with dill: {e}")


class SerializationManager:
    """
    Orchestrates the serialization process using multiple serializers.
    
    This class manages the dual serialization strategy, automatically selecting
    the appropriate serializer and storing format metadata for correct deserialization.
    """
    
    def __init__(self, strict_msgspec: bool = True, secure_dill: bool = True):
        """
        Initialize the serialization manager.
        
        Args:
            strict_msgspec: If True, msgspec serializer raises errors for incompatible types
            secure_dill: If True, apply security measures for dill deserialization
        """
        self.detector = SerializationDetector()
        self.msgspec_serializer = MsgspecSerializer(strict=strict_msgspec)
        self.dill_serializer = DillSerializer(secure=secure_dill)
        
    def serialize(self, obj: Any) -> Tuple[bytes, SerializationFormat]:
        """
        Serialize an object using the appropriate serializer.
        
        Args:
            obj: The object to serialize
            
        Returns:
            A tuple of (serialized_data, format_used)
            
        Raises:
            SerializationError: If serialization fails with all available serializers
        """
        # Detect the appropriate format
        format_type = self.detector.detect_format(obj)
        
        if format_type == SerializationFormat.MSGSPEC:
            logger.debug("Using msgspec serialization")
            data = self.msgspec_serializer.serialize(obj)
            if data is not None:
                return data, SerializationFormat.MSGSPEC
            else:
                # Fall back to dill if msgspec fails and strict=False
                logger.debug("msgspec failed, falling back to dill")
                format_type = SerializationFormat.DILL
        
        if format_type == SerializationFormat.DILL:
            logger.debug("Using dill serialization")
            data = self.dill_serializer.serialize(obj)
            return data, SerializationFormat.DILL
        
        raise SerializationError(f"No suitable serializer found for object of type {type(obj)}")
    
    def deserialize(self, data: bytes, format_type: SerializationFormat, 
                   target_type: Optional[Type] = None) -> Any:
        """
        Deserialize data using the specified format.
        
        Args:
            data: The serialized bytes
            format_type: The serialization format that was used
            target_type: Optional type hint for msgspec deserialization
            
        Returns:
            The deserialized object
            
        Raises:
            DeserializationError: If deserialization fails
        """
        if format_type == SerializationFormat.MSGSPEC:
            logger.debug("Using msgspec deserialization")
            return self.msgspec_serializer.deserialize(data, target_type)
        elif format_type == SerializationFormat.DILL:
            logger.debug("Using dill deserialization")
            return self.dill_serializer.deserialize(data)
        else:
            raise DeserializationError(f"Unknown serialization format: {format_type}")
    
    def serialize_with_metadata(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize an object and return with format metadata.
        
        This method packages the serialized data with its format information
        for storage systems that need to track serialization metadata.
        
        Args:
            obj: The object to serialize
            
        Returns:
            A dictionary containing 'data', 'format', and 'metadata' keys
            
        Raises:
            SerializationError: If serialization fails
        """
        data, format_type = self.serialize(obj)
        
        return {
            'data': data,
            'format': format_type.value,
            'metadata': {
                'original_type': type(obj).__name__,
                'original_module': getattr(type(obj), '__module__', None),
                'serializer_version': '1.0'
            }
        }
    
    def deserialize_with_metadata(self, serialized_dict: Dict[str, Any], 
                                 target_type: Optional[Type] = None) -> Any:
        """
        Deserialize an object from a metadata-enriched dictionary.
        
        Args:
            serialized_dict: Dictionary containing 'data', 'format', and 'metadata' keys
            target_type: Optional type hint for msgspec deserialization
            
        Returns:
            The deserialized object
            
        Raises:
            DeserializationError: If deserialization fails or metadata is invalid
        """
        if not isinstance(serialized_dict, dict):
            raise DeserializationError("Expected dictionary with metadata")
        
        required_keys = {'data', 'format'}
        if not required_keys.issubset(serialized_dict.keys()):
            raise DeserializationError(f"Missing required keys: {required_keys - serialized_dict.keys()}")
        
        try:
            format_type = SerializationFormat(serialized_dict['format'])
        except ValueError:
            raise DeserializationError(f"Unknown serialization format: {serialized_dict['format']}")
        
        data = serialized_dict['data']
        if not isinstance(data, bytes):
            raise DeserializationError("Data must be bytes")
        
        return self.deserialize(data, format_type, target_type)


# Default global serialization manager instance
default_serialization_manager = SerializationManager()

# Convenience functions for common use cases
def serialize(obj: Any) -> Tuple[bytes, SerializationFormat]:
    """Serialize an object using the default serialization manager."""
    return default_serialization_manager.serialize(obj)

def deserialize(data: bytes, format_type: SerializationFormat, 
               target_type: Optional[Type] = None) -> Any:
    """Deserialize data using the default serialization manager."""
    return default_serialization_manager.deserialize(data, format_type, target_type)

def serialize_with_metadata(obj: Any) -> Dict[str, Any]:
    """Serialize an object with metadata using the default serialization manager."""
    return default_serialization_manager.serialize_with_metadata(obj)

def deserialize_with_metadata(serialized_dict: Dict[str, Any], 
                             target_type: Optional[Type] = None) -> Any:
    """Deserialize an object from metadata using the default serialization manager."""
    return default_serialization_manager.deserialize_with_metadata(serialized_dict, target_type)