"""Configuration loader for OmniQ.

This module provides functions to load configurations from different sources:
- Python dictionaries
- YAML files
- Python objects
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def from_dict(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Load configuration from a Python dictionary.
    
    Args:
        config_dict: Dictionary containing configuration values
        
    Returns:
        Validated configuration dictionary
    """
    if not isinstance(config_dict, dict):
        raise TypeError("Configuration must be a dictionary")
    
    return config_dict.copy()


def from_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from a YAML file.
    
    Args:
        file_path: Path to the YAML configuration file
        
    Returns:
        Configuration dictionary loaded from YAML
        
    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If the configuration file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
    """
    if not HAS_YAML:
        raise ImportError(
            "PyYAML is required to load YAML configuration files. "
            "Install it with: pip install pyyaml"
        )
    
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in configuration file {file_path}: {e}")
    
    if config is None:
        return {}
    
    if not isinstance(config, dict):
        raise TypeError(f"Configuration file {file_path} must contain a dictionary at the root level")
    
    return config


def from_object(obj: Any) -> Dict[str, Any]:
    """Load configuration from a Python object.
    
    Extracts all uppercase attributes from the object as configuration values.
    
    Args:
        obj: Python object containing configuration attributes
        
    Returns:
        Configuration dictionary with uppercase attributes
    """
    config = {}
    
    for attr_name in dir(obj):
        # Skip private attributes and methods
        if attr_name.startswith('_'):
            continue
            
        # Only include uppercase attributes (configuration constants)
        if attr_name.isupper():
            config[attr_name.lower()] = getattr(obj, attr_name)
    
    return config


def from_env_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from a .env file.
    
    Args:
        file_path: Path to the .env file
        
    Returns:
        Configuration dictionary with OMNIQ_ prefixed variables
        
    Raises:
        FileNotFoundError: If the .env file doesn't exist
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Environment file not found: {file_path}")
    
    config = {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE format
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Remove quotes from value if present
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            
            # Only include OMNIQ_ prefixed variables
            if key.startswith('OMNIQ_'):
                # Convert to lowercase and remove prefix for internal use
                config_key = key[6:].lower()  # Remove 'OMNIQ_' prefix
                config[config_key] = value
    
    return config


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple configuration dictionaries.
    
    Later configurations override earlier ones.
    
    Args:
        *configs: Configuration dictionaries to merge
        
    Returns:
        Merged configuration dictionary
    """
    merged = {}
    
    for config in configs:
        if isinstance(config, dict):
            merged.update(config)
    
    return merged


def validate_config(config: Dict[str, Any], required_keys: Optional[list] = None) -> Dict[str, Any]:
    """Validate a configuration dictionary.
    
    Args:
        config: Configuration dictionary to validate
        required_keys: List of required configuration keys
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ValueError: If required keys are missing
    """
    if not isinstance(config, dict):
        raise TypeError("Configuration must be a dictionary")
    
    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")
    
    return config