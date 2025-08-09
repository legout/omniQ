"""Default settings for OmniQ library.

This module defines default settings as Python constants without the "OMNIQ_" prefix.
These constants can be overridden by environment variables with the "OMNIQ_" prefix.
"""

# Logging Configuration
LOG_LEVEL = "INFO"
DISABLE_LOGGING = False

# Task Queue Configuration
TASK_QUEUE_TYPE = "file"
TASK_QUEUE_URL = None

# Result Storage Configuration
RESULT_STORAGE_TYPE = "file"
RESULT_STORAGE_URL = None

# Event Storage Configuration
EVENT_STORAGE_TYPE = "sqlite"
EVENT_STORAGE_URL = None

# File System Configuration
FSSPEC_URI = "file://"
BASE_DIR = "./omniq_data"

# Worker Configuration
DEFAULT_WORKER = "async"
MAX_WORKERS = 4
THREAD_WORKERS = 4
PROCESS_WORKERS = 2
GEVENT_WORKERS = 100

# Task Configuration
TASK_TIMEOUT = 300  # 5 minutes in seconds
TASK_TTL = 3600  # 1 hour in seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # 1 second

# Result Configuration
RESULT_TTL = 86400  # 24 hours in seconds

# Component Log Levels (JSON string format for environment variable)
COMPONENT_LOG_LEVELS = "{}"

# Project Configuration
PROJECT_NAME = "omniq"

# Queue Configuration
DEFAULT_QUEUES = ["default"]