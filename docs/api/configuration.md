# API - Configuration

This section provides a detailed API reference for OmniQ's configuration system. OmniQ's configuration is managed primarily through the `OmniQConfig` class, which allows for flexible and hierarchical setup of the library's various components.

## `omniq.config.OmniQConfig`

The central configuration class for OmniQ. Instances of this class hold all the settings that define how OmniQ components behave.

### Parameters

*   `log_level` (`str`, optional): The logging level for OmniQ. Defaults to `INFO`.
    *   **Allowed Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `DISABLED`
*   `task_queue_type` (`str`, optional): The type of backend to use for the task queue. Defaults to `memory`.
    *   **Allowed Values**: `memory`, `file`, `sqlite`, `postgres`, `redis`, `nats`
*   `task_queue_path` (`str`, optional): Path specific to file/sqlite task queue backends.
*   `result_storage_type` (`str`, optional): The type of backend to use for result storage. Defaults to `memory`.
    *   **Allowed Values**: `memory`, `file`, `sqlite`, `postgres`, `redis`, `nats`
*   `result_storage_path` (`str`, optional): Path specific to file/sqlite result storage backends.
*   `event_storage_type` (`str`, optional): The type of backend to use for event storage. Defaults to `memory`.
    *   **Allowed Values**: `memory`, `file`, `sqlite`, `postgres`, `redis`, `nats`
*   `event_storage_path` (`str`, optional): Path specific to file/sqlite event storage backends.
*   `default_worker` (`str`, optional): The default worker type to use. Defaults to `async`.
    *   **Allowed Values**: `async`, `thread`, `process`, `gevent`
*   `task_ttl` (`int`, optional): Default Time-To-Live (TTL) for tasks in seconds. Tasks older than this might be purged. Defaults to `3600` (1 hour).
*   `result_ttl` (`int`, optional): Default Time-To-Live (TTL) for task results in seconds. Results older than this might be purged. Defaults to `86400` (24 hours).

### Example Usage

```python
from omniq.config import OmniQConfig

# Create a basic configuration
config = OmniQConfig(
    log_level="DEBUG",
    task_queue_type="redis",
    result_storage_type="sqlite",
    event_storage_type="file",
    task_ttl=7200 # 2 hours
)

# You can then pass this config object to your OmniQ instance
from omniq import OmniQ
omniq_instance = OmniQ(config=config)
```

## Environment Variables

OmniQ also supports configuration via environment variables. These variables follow a convention: `OMNIQ_` prefix followed by the uppercase version of the configuration parameter name. Environment variables take precedence over default values and values loaded from YAML files.

| Environment Variable        | Corresponds to `OmniQConfig` Parameter |
|-----------------------------|----------------------------------------|
| `OMNIQ_LOG_LEVEL`           | `log_level`                            |
| `OMNIQ_TASK_QUEUE_TYPE`     | `task_queue_type`                      |
| `OMNIQ_TASK_QUEUE_PATH`     | `task_queue_path`                      |
| `OMNIQ_RESULT_STORAGE_TYPE` | `result_storage_type`                  |
| `OMNIQ_RESULT_STORAGE_PATH` | `result_storage_path`                  |
| `OMNIQ_EVENT_STORAGE_TYPE`  | `event_storage_type`                   |
| `OMNIQ_EVENT_STORAGE_PATH`  | `event_storage_path`                   |
| `OMNIQ_DEFAULT_WORKER`      | `default_worker`                       |
| `OMNIQ_TASK_TTL`            | `task_ttl`                             |
| `OMNIQ_RESULT_TTL`          | `result_ttl`                           |

## Backend-Specific Configuration

For backends that require specific connection details (e.g., host, port, credentials), these parameters can be passed directly to the `OmniQConfig` constructor or set via environment variables. OmniQ automatically routes these parameters to the correct backend upon initialization.

For example, for a Redis backend:

```python
from omniq.config import OmniQConfig

config = OmniQConfig(
    task_queue_type="redis",
    redis_host="my_redis_server",
    redis_port=6379,
    redis_db=1
)
```

And via environment variables:

```bash
export OMNIQ_TASK_QUEUE_TYPE=redis
export OMNIQ_REDIS_HOST=my_redis_server
export OMNIQ_REDIS_PORT=6379
export OMNIQ_REDIS_DB=1
```

This flexible configuration system allows OmniQ to be easily deployed and adapted to various environments and infrastructure setups.