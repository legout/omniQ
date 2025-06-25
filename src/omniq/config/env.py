# src/omniq/config/env.py
"""Environment variable configuration for OmniQ."""

import os
import json
from typing import Any

from omniq.config import settings

# Helper function to get environment variables
def _get_env(name: str, default: Any = None) -> Any:
    """Get environment variable with OMNIQ_ prefix."""
    return os.environ.get(f"OMNIQ_{name}", default)

# General settings
PROJECT_NAME = _get_env("PROJECT_NAME", settings.PROJECT_NAME)
BASE_DIR = _get_env("BASE_DIR", settings.BASE_DIR)

# Task Queue settings
TASK_QUEUE_TYPE = _get_env("TASK_QUEUE_TYPE", settings.TASK_QUEUE_TYPE)
TASK_QUEUE_URL = _get_env("TASK_QUEUE_URL", settings.TASK_QUEUE_URL)

# Result Storage settings
RESULT_STORAGE_TYPE = _get_env("RESULT_STORAGE_TYPE", settings.RESULT_STORAGE_TYPE)
RESULT_STORAGE_URL = _get_env("RESULT_STORAGE_URL", settings.RESULT_STORAGE_URL)

# Event Storage settings
EVENT_STORAGE_TYPE = _get_env("EVENT_STORAGE_TYPE", settings.EVENT_STORAGE_TYPE)
EVENT_STORAGE_URL = _get_env("EVENT_STORAGE_URL", settings.EVENT_STORAGE_URL)

# Worker settings
DEFAULT_WORKER = _get_env("DEFAULT_WORKER", settings.DEFAULT_WORKER)
MAX_WORKERS = int(_get_env("MAX_WORKERS", settings.MAX_WORKERS))
THREAD_WORKERS = int(_get_env("THREAD_WORKERS", settings.THREAD_WORKERS))
PROCESS_WORKERS = int(_get_env("PROCESS_WORKERS", settings.PROCESS_WORKERS))
GEVENT_WORKERS = int(_get_env("GEVENT_WORKERS", settings.GEVENT_WORKERS))

# Task settings
TASK_TIMEOUT = int(_get_env("TASK_TIMEOUT", settings.TASK_TIMEOUT))
TASK_TTL = int(_get_env("TASK_TTL", settings.TASK_TTL))
RETRY_ATTEMPTS = int(_get_env("RETRY_ATTEMPTS", settings.RETRY_ATTEMPTS))
RETRY_DELAY = int(_get_env("RETRY_DELAY", settings.RETRY_DELAY))
RESULT_TTL = int(_get_env("RESULT_TTL", settings.RESULT_TTL))

# Dashboard settings
DASHBOARD_PORT = int(_get_env("DASHBOARD_PORT", settings.DASHBOARD_PORT))
DASHBOARD_ENABLED = _get_env("DASHBOARD_ENABLED", settings.DASHBOARD_ENABLED) in ("1", "true", "True")

# Logging settings
LOG_LEVEL = _get_env("LOG_LEVEL", settings.LOG_LEVEL)
DISABLE_LOGGING = _get_env("DISABLE_LOGGING", settings.DISABLE_LOGGING) in ("1", "true", "True")

# Component log levels
COMPONENT_LOG_LEVELS = settings.COMPONENT_LOG_LEVELS
component_log_levels_str = _get_env("COMPONENT_LOG_LEVELS")
if component_log_levels_str:
    try:
        COMPONENT_LOG_LEVELS = json.loads(component_log_levels_str)
    except json.JSONDecodeError:
        pass