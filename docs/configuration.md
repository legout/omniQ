# Configuration

This section will detail the various methods for configuring OmniQ.

OmniQ provides multiple configuration methods:

- Direct parameter initialization
- Type-validated config objects using msgspec.Struct
- Dictionary-based configuration
- YAML file configuration
- Environment variable overrides

## Settings and Environment Variables

- Define settings constants without "OMNIQ_" prefix
- Override settings with environment variables with "OMNIQ_" prefix
- Example: `BASE_DIR` in settings, `OMNIQ_BASE_DIR` as environment variable

```python
# settings.py
BASE_DIR = "default/path"
PROJECT_NAME = "default"

# env.py
import os
from .settings import BASE_DIR, PROJECT_NAME

base_dir = os.environ.get("OMNIQ_BASE_DIR", BASE_DIR)
project_name = os.environ.get("OMNIQ_PROJECT_NAME", PROJECT_NAME)
```

Support the following variables:
- `LOG_LEVEL` in settings, `OMNIQ_LOG_LEVEL` as env var: Set library logging level (DEBUG, INFO, WARNING, ERROR, DISABLED)
- `DISABLE_LOGGING` in settings, `OMNIQ_DISABLE_LOGGING` as env var: Disable all library logging when set to "1" or "true"
- `TASK_QUEUE_TYPE` in settings, `OMNIQ_TASK_QUEUE_TYPE` as env var: Queue backend for tasks (file, memory, sqlite, postgres, redis, nats)
- `TASK_QUEUE_URL` in settings, `OMNIQ_TASK_QUEUE_URL` as env var: Connection string for task queue backend
- `RESULT_STORAGE_TYPE` in settings, `OMNIQ_RESULT_STORAGE_TYPE` as env var: Storage backend for results (file, memory, sqlite, postgres, redis, nats)
- `RESULT_STORAGE_URL` in settings, `OMNIQ_RESULT_STORAGE_URL` as env var: Connection string for result storage backend
- `EVENT_STORAGE_TYPE` in settings, `OMNIQ_EVENT_STORAGE_TYPE` as env var: Storage backend for events (sqlite, postgres, file)
- `EVENT_STORAGE_URL` in settings, `OMNIQ_EVENT_STORAGE_URL` as env var: Connection string for event storage backend
- `FSSPEC_URI` in settings, `OMNIQ_FSSPEC_URI` as env var: URI for fsspec (e.g., "file:///path", "s3://bucket", "memory://")
- `DEFAULT_WORKER` in settings, `OMNIQ_DEFAULT_WORKER` as env var: Default worker type (async, thread, process, gevent)
- `MAX_WORKERS` in settings, `OMNIQ_MAX_WORKERS` as env var: Maximum number of workers
- `THREAD_WORKERS` in settings, `OMNIQ_THREAD_WORKERS` as env var: Thread pool size
- `PROCESS_WORKERS` in settings, `OMNIQ_PROCESS_WORKERS` as env var: Process pool size
- `GEVENT_WORKERS` in settings, `OMNIQ_GEVENT_WORKERS` as env var: Gevent pool size
- `TASK_TIMEOUT` in settings, `OMNIQ_TASK_TIMEOUT` as env var: Default task execution timeout in seconds
- `TASK_TTL` in settings, `OMNIQ_TASK_TTL` as env var: Default time-to-live for tasks in seconds
- `RETRY_ATTEMPTS` in settings, `OMNIQ_RETRY_ATTEMPTS` as env var: Default number of retry attempts
- `RETRY_DELAY` in settings, `OMNIQ_RETRY_DELAY` as env var: Default delay between retries in seconds
- `RESULT_TTL` in settings, `OMNIQ_RESULT_TTL` as env var: Default time-to-live for task results in seconds
- `COMPONENT_LOG_LEVELS` in settings, `OMNIQ_COMPONENT_LOG_LEVELS` as env var: JSON string with per-component logging levels

## Component Configuration

- Use msgspec.Struct for type-validated configuration
- Support multiple initialization methods:
  - Direct parameters
  - Config objects
  - Dictionaries
  - YAML files

```python
@classmethod
def from_config(cls, config):
    """Create instance from config object"""
    return cls(**config.dict())

@classmethod
def from_dict(cls, config_dict):
    """Create instance from dictionary"""
    return cls(**config_dict)

@classmethod
def from_config_file(cls, config_path):
    """Create instance from config file"""
    config_dict = load_yaml_config(config_path)
    return cls.from_dict(config_dict)
```