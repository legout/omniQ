# Configuration

OmniQ provides flexible configuration options through various methods, including environment variables, YAML files, and direct code.

## Configuration Hierarchy

OmniQ loads configuration in a specific order, with later sources overriding earlier ones:

1.  **Default Settings**: Built-in default values.
2.  **YAML Files**: Configuration loaded from specified YAML files.
3.  **Environment Variables**: Variables prefixed with `OMNIQ_` override corresponding settings.

## Environment Variables

Environment variables are a convenient way to configure OmniQ, especially in deployment environments. All OmniQ-specific environment variables are prefixed with `OMNIQ_`.

| Environment Variable      | Description                                     | Example Value           |
|---------------------------|-------------------------------------------------|-------------------------|
| `OMNIQ_LOG_LEVEL`         | Sets the logging level for OmniQ.               | `INFO`, `DEBUG`, `ERROR`|
| `OMNIQ_TASK_QUEUE_TYPE`   | Specifies the backend for task queues.          | `file`, `memory`, `redis`|
| `OMNIQ_RESULT_STORAGE_TYPE`| Specifies the backend for result storage.       | `file`, `memory`, `sqlite`|
| `OMNIQ_EVENT_STORAGE_TYPE`| Specifies the backend for event storage.        | `file`, `sqlite`, `postgres`|
| `OMNIQ_DEFAULT_WORKER`    | Sets the default worker type.                   | `async`, `thread`, `process`|
| `OMNIQ_TASK_TTL`          | Default time-to-live for tasks in seconds.      | `3600` (1 hour)         |
| `OMNIQ_RESULT_TTL`        | Default time-to-live for task results in seconds.| `86400` (24 hours)      |

## YAML Configuration

You can define OmniQ settings in a YAML file. This allows for more structured and readable configurations.

Example `config.yaml`:

```yaml
log_level: DEBUG
task_queue:
  type: redis
  host: localhost
  port: 6379
result_storage:
  type: sqlite
  database: omniq_results.db
```

To load a YAML configuration, you would typically pass the path to your OmniQ instance or a configuration loader.

## Code Configuration

For programmatic control, you can configure OmniQ directly in your Python code.

```python
from omniq import OmniQ
from omniq.config import OmniQConfig

config = OmniQConfig(
    log_level="DEBUG",
    task_queue_type="memory",
    result_storage_type="memory"
)

omniq = OmniQ(config=config)
# Use omniq instance
```

## Advanced Configuration

OmniQ's modular design allows for fine-grained control over each component's configuration. For instance, you can configure different backends for task queues, result storage, and event storage independently.

```python
from omniq import OmniQ
from omniq.config import OmniQConfig
from omniq.backend import FileBackend, SQLiteBackend

config = OmniQConfig(
    task_queue_backend=FileBackend(base_dir="./tasks"),
    result_storage_backend=SQLiteBackend(database_path="results.db")
)

omniq = OmniQ(config=config)
```

This flexibility ensures OmniQ can adapt to various architectural requirements and deployment scenarios.