"""Configuration system for OmniQ.

This package provides a flexible configuration system that supports:
- Default settings as Python constants
- Environment variable overrides with OMNIQ_ prefix
- Configuration loading from dictionaries, YAML files, and Python objects
- Type-validated configuration objects using msgspec.Struct
"""

from . import settings
from . import env
from . import loader

__all__ = [
    "settings",
    "env", 
    "loader"
]