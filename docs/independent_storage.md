# Independent Storage Backend Selection

OmniQ supports independent storage backend selection, allowing you to use different storage backends for different components. This provides flexibility in deployment scenarios where you might want to optimize each component for its specific use case.

## Overview

OmniQ has four main storage components:

1. **Task Queue** - Stores pending and active tasks
2. **Result Storage** - Stores task execution results
3. **Event Storage** - Stores task lifecycle events
4. **Schedule Storage** - Stores scheduled task definitions

With independent storage selection, you can configure each component to use a different backend based on your requirements.

## Supported Storage Backends

- **SQLite** - File-based SQL database, good for single-machine deployments
- **Memory** - In-memory storage, fast but ephemeral (good for testing)
- **File** - File system storage with various serialization formats
- **Redis** - In-memory data store with persistence options
- **PostgreSQL** - Full-featured SQL database for production deployments
- **NATS** - Message streaming system for distributed deployments

*Note: Some backends may not be fully implemented yet. The factory system gracefully handles missing implementations.*

## Configuration Methods

### 1. Environment Variables

Set environment variables with the `OMNIQ_` prefix:

```bash
# Task queue configuration
export OMNIQ_TASK_QUEUE_TYPE="sqlite"
export OMNIQ_TASK_QUEUE_URL="sqlite:///tasks.db"

# Result storage configuration
export OMNIQ_RESULT_STORAGE_TYPE="file"
export OMNIQ_RESULT_STORAGE_URL="./results"

# Event storage configuration
export OMNIQ_EVENT_STORAGE_TYPE="memory"

# Schedule storage configuration
export OMNIQ_SCHEDULE_STORAGE_TYPE="sqlite"
export OMNIQ_SCHEDULE_STORAGE_URL="sqlite:///schedules.db"
```

Then create OmniQ instance:

```python
from omniq import OmniQ

# Configuration will be loaded from environment variables
omniq = OmniQ()
```

### 2. Programmatic Configuration

```python
from omniq import OmniQ
from omniq.models.config import OmniQConfig, StorageBackendConfig

config = OmniQConfig(
    task_queue_backend=StorageBackendConfig(
        backend_type="sqlite",
        url="sqlite:///tasks.db"
    ),
    result_storage_backend=StorageBackendConfig(
        backend_type="file",
        config={
            "base_dir": "./results",
            "serialization_format": "json"
        }
    ),
    event_storage_backend=StorageBackendConfig(
        backend_type="memory"
    ),
    schedule_storage_backend=StorageBackendConfig(
        backend_type="sqlite",
        url="sqlite:///schedules.db"
    )
)

omniq = OmniQ(config=config)
```

### 3. YAML Configuration

Create a YAML configuration file:

```yaml
# config.yaml
project_name: "my_omniq_app"

task_queue_backend:
  backend_type: "sqlite"
  url: "sqlite:///tasks.db"

result_storage_backend:
  backend_type: "file"
  config:
    base_dir: "./results"
    serialization_format: "json"

event_storage_backend:
  backend_type: "memory"

schedule_storage_backend:
  backend_type: "sqlite"
  url: "sqlite:///schedules.db"

default_ttl: 3600
log_level: "INFO"
```

Load the configuration:

```python
from omniq import OmniQ
from omniq.models.config import OmniQConfig

config = OmniQConfig.from_yaml("config.yaml")
omniq = OmniQ(config=config)
```

## Backend-Specific Configuration

### SQLite Backend

```python
StorageBackendConfig(
    backend_type="sqlite",
    url="sqlite:///database.db",  # or just "database.db"
    config={
        "timeout": 30.0,
        "journal_mode": "WAL",
        "synchronous": "NORMAL",
        "cache_size": -64000  # 64MB
    }
)
```

### File Backend

```python
StorageBackendConfig(
    backend_type="file",
    config={
        "base_dir": "./data",
        "serialization_format": "json",  # json, msgpack, pickle
        "fsspec_uri": None,  # or "s3://bucket" for cloud storage
        "storage_options": {}  # fsspec storage options
    }
)
```

### Memory Backend

```python
StorageBackendConfig(
    backend_type="memory"
    # No additional configuration needed
)
```

### Redis Backend

```python
StorageBackendConfig(
    backend_type="redis",
    url="redis://localhost:6379/0",
    config={
        "host": "localhost",
        "port": 6379,
        "database": 0,
        "password": None,
        "max_connections": 10
    }
)
```

### PostgreSQL Backend

```python
StorageBackendConfig(
    backend_type="postgres",
    url="postgresql://user:pass@localhost:5432/omniq",
    config={
        "host": "localhost",
        "port": 5432,
        "database": "omniq",
        "username": "user",
        "password": "pass",
        "min_connections": 1,
        "max_connections": 10
    }
)
```

## Common Deployment Scenarios

### Development/Testing

Use memory storage for all components for fast, ephemeral testing:

```python
config = OmniQConfig(
    task_queue_backend=StorageBackendConfig(backend_type="memory"),
    result_storage_backend=StorageBackendConfig(backend_type="memory"),
    event_storage_backend=StorageBackendConfig(backend_type="memory"),
    schedule_storage_backend=StorageBackendConfig(backend_type="memory")
)
```

### Single Machine Production

Use SQLite for all components:

```python
config = OmniQConfig(
    task_queue_backend=StorageBackendConfig(
        backend_type="sqlite", url="sqlite:///omniq.db"
    ),
    result_storage_backend=StorageBackendConfig(
        backend_type="sqlite", url="sqlite:///omniq.db"
    ),
    event_storage_backend=StorageBackendConfig(
        backend_type="sqlite", url="sqlite:///omniq.db"
    ),
    schedule_storage_backend=StorageBackendConfig(
        backend_type="sqlite", url="sqlite:///omniq.db"
    )
)
```

### Optimized Production

Use different backends optimized for each component:

```python
config = OmniQConfig(
    # SQLite for reliable task persistence
    task_queue_backend=StorageBackendConfig(
        backend_type="sqlite", url="sqlite:///tasks.db"
    ),
    
    # File storage for large result data
    result_storage_backend=StorageBackendConfig(
        backend_type="file",
        config={"base_dir": "/var/omniq/results"}
    ),
    
    # Redis for fast event logging
    event_storage_backend=StorageBackendConfig(
        backend_type="redis", url="redis://localhost:6379/1"
    ),
    
    # PostgreSQL for complex schedule queries
    schedule_storage_backend=StorageBackendConfig(
        backend_type="postgres",
        url="postgresql://user:pass@localhost:5432/schedules"
    )
)
```

## Fallback Behavior

If a specific backend configuration is not provided, OmniQ will fall back to:

1. Environment variables (e.g., `OMNIQ_TASK_QUEUE_TYPE`)
2. The task queue backend configuration for other components
3. SQLite as the default backend

This ensures backward compatibility with existing configurations.

## Legacy Backend Support

OmniQ still supports the legacy single-backend approach for backward compatibility:

```python
from omniq.backend.sqlite import SQLiteBackend

# Legacy approach - single backend for all components
backend = SQLiteBackend()
omniq = OmniQ(backend=backend)
```

When using a legacy backend, all storage components will use the same backend instance.

## Best Practices

1. **Development**: Use memory storage for all components for fast testing
2. **Single Machine**: Use SQLite for all components for simplicity
3. **Production**: Consider using different backends optimized for each component:
   - SQLite/PostgreSQL for task queue (reliability)
   - File/S3 for result storage (large data)
   - Redis/Memory for event storage (speed)
   - PostgreSQL for schedule storage (complex queries)

4. **Monitoring**: Use appropriate log levels for each component
5. **Backup**: Ensure persistent backends are properly backed up
6. **Performance**: Monitor storage performance and adjust configurations as needed

## Examples

See the `examples/` directory for complete working examples:

- `examples/independent_storage_example.py` - Comprehensive usage examples
- `examples/deployment_configs/` - Various deployment configuration files

## Troubleshooting

### Missing Backend Implementation

If you try to use a backend that's not implemented, you'll get a clear error message:

```
ValueError: Unsupported task queue backend: redis
```

Check the factory implementation in `src/omniq/storage/factory.py` to see which backends are available.

### Connection Issues

Storage components with connection issues will be handled gracefully. Check the logs for connection warnings and errors.

### Configuration Validation

Invalid configurations will raise `ValueError` with descriptive messages about what's wrong and how to fix it.