# src/omniq/config/settings.py
"""Default settings for OmniQ."""

# General settings
PROJECT_NAME = "omniq"
BASE_DIR = "."

# Task Queue settings
TASK_QUEUE_TYPE = "memory"
TASK_QUEUE_URL = None

# Result Storage settings
RESULT_STORAGE_TYPE = "memory"
RESULT_STORAGE_URL = None

# Event Storage settings
EVENT_STORAGE_TYPE = None
EVENT_STORAGE_URL = None

# Worker settings
DEFAULT_WORKER = "thread_pool"
MAX_WORKERS = 10
THREAD_WORKERS = 10
PROCESS_WORKERS = 4
GEVENT_WORKERS = 100

# Task settings
TASK_TIMEOUT = 60 * 60  # 1 hour
TASK_TTL = 60 * 60 * 24  # 24 hours
RETRY_ATTEMPTS = 3
RETRY_DELAY = 60  # 60 seconds
RESULT_TTL = 60 * 60 * 24  # 24 hours

# Dashboard settings
DASHBOARD_PORT = 8080
DASHBOARD_ENABLED = False

# Logging settings
LOG_LEVEL = "INFO"
DISABLE_LOGGING = False
COMPONENT_LOG_LEVELS = {}