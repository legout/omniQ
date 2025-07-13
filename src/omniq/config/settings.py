"""Library settings constants (no OMNIQ_ prefix)."""

from pathlib import Path

# Base configuration
BASE_DIR = str(Path.home() / ".omniq")
LOG_LEVEL = "INFO"
DEBUG = False

# Queue configuration
TASK_QUEUE_TYPE = "sqlite"
RESULT_STORAGE_TYPE = "sqlite"
EVENT_STORAGE_TYPE = "sqlite"
DEFAULT_QUEUE_NAME = "default"

# Worker configuration
DEFAULT_WORKER = "async"
WORKER_POOL_SIZE = 4
MAX_WORKER_POOL_SIZE = 16
WORKER_HEARTBEAT_INTERVAL = 30.0
WORKER_SHUTDOWN_TIMEOUT = 30.0

# Task configuration
TASK_TTL = 86400  # 24 hours in seconds
RESULT_TTL = 86400  # 24 hours in seconds
EVENT_TTL = 604800  # 7 days in seconds
MAX_RETRIES = 3
RETRY_DELAY = 1.0
RETRY_BACKOFF = "exponential"
TASK_TIMEOUT = 300  # 5 minutes in seconds

# Queue behavior
QUEUE_POLLING_INTERVAL = 1.0
QUEUE_BATCH_SIZE = 1
QUEUE_MAX_SIZE = None
QUEUE_PRIORITY_ENABLED = True

# Storage configuration
STORAGE_CONNECTION_TIMEOUT = 30.0
STORAGE_POOL_SIZE = 5
STORAGE_MAX_OVERFLOW = 10
STORAGE_COMPRESSION = False

# Serialization
SERIALIZATION_PRIMARY = "msgspec"
SERIALIZATION_FALLBACK = "dill"
SERIALIZATION_COMPRESSION = False

# Event logging
EVENT_LOGGING_ENABLED = True
EVENT_BATCH_SIZE = 100
EVENT_FLUSH_INTERVAL = 5.0
EVENT_MAX_BUFFER_SIZE = 10000
EVENT_ASYNC_PROCESSING = True

# Maintenance and cleanup
CLEANUP_INTERVAL = 3600  # 1 hour in seconds
CLEANUP_ENABLED = True
HEALTH_CHECK_INTERVAL = 60.0
HEALTH_CHECK_ENABLED = True

# Performance and limits
MAX_TASK_SIZE_MB = 10
MAX_RESULT_SIZE_MB = 10
MAX_EVENT_SIZE_MB = 1
CONNECTION_POOL_TIMEOUT = 30.0

# Development and debugging
METRICS_ENABLED = False
TRACING_ENABLED = False
PROFILING_ENABLED = False