"""SerializationDetector and Manager for intelligent serialization."""

from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union

import msgspec


class BaseSerializer(ABC):
    """Abstract base class for serializers."""
    
    @abstractmethod
    def can_serialize(self, obj: Any) -> bool:
        """Check if this serializer can handle the object."""
        pass
    
    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """Serialize object to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes to object."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Serializer name for identification."""
        pass


class SerializationDetector:
    """Detects serialization compatibility for different object types."""
    
    # Types that msgspec can handle natively
    MSGSPEC_COMPATIBLE_TYPES = {
        type(None),
        bool,
        int,
        float,
        str,
        bytes,
        bytearray,
        list,
        tuple,
        dict,
        set,
        frozenset,
    }
    
    # Types that definitely need dill
    DILL_REQUIRED_TYPES = {
        type(lambda: None),  # function
        type,  # class/type
        type(inspect),  # module
    }
    
    @classmethod
    def is_msgspec_compatible(cls, obj: Any) -> bool:
        """Check if object is compatible with msgspec serialization."""
        obj_type = type(obj)
        
        # Check basic types
        if obj_type in cls.MSGSPEC_COMPATIBLE_TYPES:
            return True
        
        # Check if it's a msgspec.Struct
        if hasattr(obj, "__struct_fields__"):
            return True
        
        # Check for types that definitely need dill
        if obj_type in cls.DILL_REQUIRED_TYPES:
            return False
        
        # Check for callable objects (excluding classes with __call__)
        if callable(obj) and not hasattr(obj, "__dict__"):
            return False
        
        # Check for objects with __dict__ (might be serializable)
        if hasattr(obj, "__dict__"):
            # Simple objects with basic attributes might work
            if cls._has_simple_dict(obj):
                return True
            return False
        
        # Check collections recursively (but limit depth)
        if isinstance(obj, (list, tuple)):
            return all(cls.is_msgspec_compatible(item) for item in obj[:10])  # Limit check
        
        if isinstance(obj, dict):
            items = list(obj.items())[:10]  # Limit check
            return all(
                cls.is_msgspec_compatible(k) and cls.is_msgspec_compatible(v)
                for k, v in items
            )
        
        if isinstance(obj, (set, frozenset)):
            items = list(obj)[:10]  # Limit check
            return all(cls.is_msgspec_compatible(item) for item in items)
        
        # Default to False for unknown types
        return False
    
    @classmethod
    def _has_simple_dict(cls, obj: Any) -> bool:
        """Check if object has a simple __dict__ with basic types."""
        if not hasattr(obj, "__dict__"):
            return False
        
        obj_dict = obj.__dict__
        if not isinstance(obj_dict, dict):
            return False
        
        # Check a few items to see if they're basic types
        items = list(obj_dict.items())[:5]
        for key, value in items:
            if not isinstance(key, str):
                return False
            if not cls.is_msgspec_compatible(value):
                return False
        
        return True
    
    @classmethod
    def recommend_serializer(cls, obj: Any) -> str:
        """Recommend the best serializer for the object."""
        if cls.is_msgspec_compatible(obj):
            return "msgspec"
        return "dill"


class SerializationManager:
    """Manages multiple serializers with intelligent fallback."""
    
    def __init__(self):
        self._serializers: Dict[str, BaseSerializer] = {}
        self._detector = SerializationDetector()
    
    def register_serializer(self, serializer: BaseSerializer) -> None:
        """Register a serializer."""
        self._serializers[serializer.name] = serializer
    
    def get_serializer(self, name: str) -> Optional[BaseSerializer]:
        """Get serializer by name."""
        return self._serializers.get(name)
    
    def detect_serializer(self, obj: Any) -> str:
        """Detect the best serializer for an object."""
        return self._detector.recommend_serializer(obj)
    
    def serialize(
        self,
        obj: Any,
        preferred_serializer: Optional[str] = None
    ) -> tuple[bytes, str]:
        """
        Serialize object with intelligent serializer selection.
        
        Returns:
            Tuple of (serialized_data, serializer_name)
        """
        # Try preferred serializer first
        if preferred_serializer and preferred_serializer in self._serializers:
            serializer = self._serializers[preferred_serializer]
            if serializer.can_serialize(obj):
                try:
                    data = serializer.serialize(obj)
                    return data, serializer.name
                except Exception:
                    pass  # Fall back to auto-detection
        
        # Auto-detect best serializer
        recommended = self.detect_serializer(obj)
        if recommended in self._serializers:
            serializer = self._serializers[recommended]
            try:
                data = serializer.serialize(obj)
                return data, serializer.name
            except Exception:
                pass  # Try fallback
        
        # Try all serializers as fallback
        for name, serializer in self._serializers.items():
            if name == recommended:
                continue  # Already tried
            
            try:
                if serializer.can_serialize(obj):
                    data = serializer.serialize(obj)
                    return data, serializer.name
            except Exception:
                continue
        
        raise ValueError(f"No serializer could handle object of type {type(obj)}")
    
    def deserialize(self, data: bytes, serializer_name: str) -> Any:
        """Deserialize data using specified serializer."""
        if serializer_name not in self._serializers:
            raise ValueError(f"Unknown serializer: {serializer_name}")
        
        serializer = self._serializers[serializer_name]
        return serializer.deserialize(data)
    
    def available_serializers(self) -> list[str]:
        """Get list of available serializer names."""
        return list(self._serializers.keys())