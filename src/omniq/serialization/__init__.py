"""OmniQ serialization layer.

This module provides a dual-serializer strategy for OmniQ:
- Primary serializer: msgspec (high performance for compatible types)
- Fallback serializer: dill (broad compatibility for complex objects)

The SerializationManager orchestrates the dual-serializer strategy,
automatically selecting the appropriate serializer and including
identifiers in the serialized data for proper deserialization.
"""

from .base import BaseSerializer, SerializationError, DeserializationError
from .msgspec import MsgspecSerializer
from .dill import DillSerializer
from .manager import SerializationManager, SerializerType

__all__ = [
    # Base classes and exceptions
    'BaseSerializer',
    'SerializationError',
    'DeserializationError',
    
    # Serializer implementations
    'MsgspecSerializer',
    'DillSerializer',
    
    # Manager and types
    'SerializationManager',
    'SerializerType',
]