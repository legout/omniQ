"""Environment variable configuration for OmniQ.

This module reads environment variables with the "OMNIQ_" prefix to override
the default settings defined in settings.py.
"""

import os
import json
from typing import Any, Dict, List

from . import settings


def _get_env_bool(key: str, default: bool) -> bool:
    """Get a boolean value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _get_env_int(key: str, default: int) -> int:
    """Get an integer value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(key: str, default: float) -> float:
    """Get a float value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_json(key: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """Get a JSON value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _get_env_list(key: str, default: List[str], separator: str = ",") -> List[str]:
    """Get a list value from environment variable."""
    value = os.environ.get(key)
    if value is None:
        return default
    return [item.strip() for item in value.split(separator) if item.strip()]


# Logging Configuration
log_level = os.environ.get("OMNIQ_LOG_LEVEL", settings.LOG_LEVEL)
disable_logging = _get_env_bool("OMNIQ_DISABLE_LOGGING", settings.DISABLE_LOGGING)

# Task Queue Configuration
task_queue_type = os.environ.get("OMNIQ_TASK_QUEUE_TYPE", settings.TASK_QUEUE_TYPE)
task_queue_url = os.environ.get("OMNIQ_TASK_QUEUE_URL", settings.TASK_QUEUE_URL)

# Result Storage Configuration
result_storage_type = os.environ.get("OMNIQ_RESULT_STORAGE_TYPE", settings.RESULT_STORAGE_TYPE)
result_storage_url = os.environ.get("OMNIQ_RESULT_STORAGE_URL", settings.RESULT_STORAGE_URL)

# Event Storage Configuration
event_storage_type = os.environ.get("OMNIQ_EVENT_STORAGE_TYPE", settings.EVENT_STORAGE_TYPE)
event_storage_url = os.environ.get("OMNIQ_EVENT_STORAGE_URL", settings.EVENT_STORAGE_URL)

# File System Configuration
fsspec_uri = os.environ.get("OMNIQ_FSSPEC_URI", settings.FSSPEC_URI)
base_dir = os.environ.get("OMNIQ_BASE_DIR", settings.BASE_DIR)

# Worker Configuration
default_worker = os.environ.get("OMNIQ_DEFAULT_WORKER", settings.DEFAULT_WORKER)
max_workers = _get_env_int("OMNIQ_MAX_WORKERS", settings.MAX_WORKERS)
thread_workers = _get_env_int("OMNIQ_THREAD_WORKERS", settings.THREAD_WORKERS)
process_workers = _get_env_int("OMNIQ_PROCESS_WORKERS", settings.PROCESS_WORKERS)
gevent_workers = _get_env_int("OMNIQ_GEVENT_WORKERS", settings.GEVENT_WORKERS)

# Task Configuration
task_timeout = _get_env_int("OMNIQ_TASK_TIMEOUT", settings.TASK_TIMEOUT)
task_ttl = _get_env_int("OMNIQ_TASK_TTL", settings.TASK_TTL)
retry_attempts = _get_env_int("OMNIQ_RETRY_ATTEMPTS", settings.RETRY_ATTEMPTS)
retry_delay = _get_env_float("OMNIQ_RETRY_DELAY", settings.RETRY_DELAY)

# Result Configuration
result_ttl = _get_env_int("OMNIQ_RESULT_TTL", settings.RESULT_TTL)

# Component Log Levels
component_log_levels = _get_env_json("OMNIQ_COMPONENT_LOG_LEVELS", json.loads(settings.COMPONENT_LOG_LEVELS))

# Project Configuration
project_name = os.environ.get("OMNIQ_PROJECT_NAME", settings.PROJECT_NAME)

# Queue Configuration
default_queues = _get_env_list("OMNIQ_DEFAULT_QUEUES", settings.DEFAULT_QUEUES)