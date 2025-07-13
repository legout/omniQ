"""Environment variable handling (OMNIQ_ prefix)."""

import os
from typing import Any, Dict, Optional, Type, TypeVar, Union

from . import settings


T = TypeVar("T")


def _convert_value(value: str, target_type: Type[T]) -> T:
    """Convert string value to target type."""
    if target_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    elif target_type == int:
        return int(value)
    elif target_type == float:
        return float(value)
    elif target_type == str:
        return value
    elif target_type is type(None):
        return None if value.lower() in ("none", "null", "") else value
    else:
        return target_type(value)


def get_env_var(
    name: str,
    default: T,
    prefix: str = "OMNIQ_"
) -> T:
    """
    Get environment variable with OMNIQ_ prefix and type conversion.
    
    Args:
        name: Setting name (without prefix)
        default: Default value (determines type)
        prefix: Environment variable prefix
    
    Returns:
        Environment variable value converted to default's type
    """
    env_name = f"{prefix}{name}"
    env_value = os.getenv(env_name)
    
    if env_value is None:
        return default
    
    try:
        return _convert_value(env_value, type(default))
    except (ValueError, TypeError):
        return default


def get_env_config() -> Dict[str, Any]:
    """
    Get configuration dictionary with environment variable overrides.
    
    Returns:
        Dictionary mapping setting names to values (with env overrides)
    """
    config = {}
    
    # Get all settings from the settings module
    for name in dir(settings):
        if name.isupper() and not name.startswith("_"):
            default_value = getattr(settings, name)
            config[name] = get_env_var(name, default_value)
    
    return config


def get_database_url() -> Optional[str]:
    """Get database URL from environment with common variable names."""
    possible_names = [
        "OMNIQ_DATABASE_URL",
        "DATABASE_URL",
        "DB_URL",
        "OMNIQ_DB_URL"
    ]
    
    for name in possible_names:
        url = os.getenv(name)
        if url:
            return url
    
    return None


def get_redis_url() -> Optional[str]:
    """Get Redis URL from environment with common variable names."""
    possible_names = [
        "OMNIQ_REDIS_URL",
        "REDIS_URL",
        "REDISCLOUD_URL",
        "OMNIQ_CACHE_URL"
    ]
    
    for name in possible_names:
        url = os.getenv(name)
        if url:
            return url
    
    return None


def get_storage_config() -> Dict[str, Any]:
    """Get storage-specific configuration from environment."""
    return {
        "database_url": get_database_url(),
        "redis_url": get_redis_url(),
        "s3_bucket": os.getenv("OMNIQ_S3_BUCKET"),
        "s3_region": os.getenv("OMNIQ_S3_REGION", "us-east-1"),
        "azure_container": os.getenv("OMNIQ_AZURE_CONTAINER"),
        "gcp_bucket": os.getenv("OMNIQ_GCP_BUCKET"),
        "file_base_path": os.getenv("OMNIQ_FILE_BASE_PATH"),
    }


def is_development() -> bool:
    """Check if running in development environment."""
    env = os.getenv("OMNIQ_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    return env.lower() in ("development", "dev", "local")


def is_production() -> bool:
    """Check if running in production environment."""
    env = os.getenv("OMNIQ_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    return env.lower() in ("production", "prod")


def is_testing() -> bool:
    """Check if running in test environment."""
    env = os.getenv("OMNIQ_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    return env.lower() in ("testing", "test") or os.getenv("PYTEST_CURRENT_TEST") is not None