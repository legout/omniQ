# Configuration-Based Usage Examples

This directory contains examples demonstrating the various configuration methods available in the OmniQ library, showing how to configure components using config objects, dictionaries, and YAML files.

## Files

- **`config_usage.py`**: Demonstrates configuration-based usage with config objects and YAML file loading
- **`config.yaml`**: Example YAML configuration file showing all configuration options
- **`config_usage.ipynb`**: Jupyter notebook containing interactive examples of all configuration methods

## Overview

OmniQ provides multiple flexible configuration methods to suit different use cases and preferences:

1. **Config Objects**: Type-validated configuration using `msgspec.Struct` classes
2. **Dictionary Configuration**: Simple dictionary-based configuration
3. **YAML File Configuration**: External configuration files for easy deployment
4. **Environment Variable Overrides**: Runtime configuration through environment variables

## Configuration Methods

### 1. Config Objects (Type-Validated)

Use specific config classes for type validation and IDE support:

```python
from omniq.models import FileTaskQueueConfig, SQLiteResultStorageConfig
from omniq.queue import FileTaskQueue
from omniq.storage import SQLiteResultStorage

queue = FileTaskQueue.from_config(
    FileTaskQueueConfig(
        project_name="my_project",
        base_dir="some/path",
        queues=["high", "medium", "low"]
    )
)
```

### 2. Dictionary Configuration

Simple and flexible dictionary-based configuration:

```python
from omniq import OmniQ

config = {
    "project_name": "my_project",
    "task_queue": {
        "type": "file",
        "config": {
            "base_dir": "some/path",
            "queues": ["high", "medium", "low"]
        }
    }
}

oq = OmniQ.from_dict(config)
```

### 3. YAML File Configuration

External configuration files for easy deployment and environment management:

```python
from omniq import OmniQ

# Load complete OmniQ configuration from YAML
oq = OmniQ.from_config_file("config.yaml")
```

### 4. Environment Variable Overrides

Runtime configuration through environment variables with `OMNIQ_` prefix:

```bash
export OMNIQ_TASK_QUEUE_TYPE=sqlite
export OMNIQ_RESULT_STORAGE_TYPE=file
export OMNIQ_MAX_WORKERS=20
```

## Benefits of Configuration-Based Approach

- **Type Safety**: Config objects provide compile-time type checking
- **Validation**: Automatic validation of configuration parameters
- **Documentation**: Self-documenting configuration with clear structure
- **Environment Management**: Easy switching between development, staging, and production
- **Version Control**: Configuration files can be versioned and tracked
- **Deployment**: Simplified deployment with external configuration files
- **Flexibility**: Mix and match different configuration methods as needed

## When to Use Configuration-Based Approach

Use this approach when you need:

- **Environment-specific configurations** (dev, staging, production)
- **Type validation** and IDE support for configuration
- **External configuration management** separate from code
- **Complex configurations** with many components and options
- **Team collaboration** with shared configuration standards
- **Deployment automation** with configuration templates

## Configuration Structure

The YAML configuration supports the following structure:

```yaml
project_name: my_project

task_queue:
  type: file|memory|sqlite|postgres|redis|nats
  config:
    # Type-specific configuration options

result_store:
  type: file|memory|sqlite|postgres|redis|nats
  config:
    # Type-specific configuration options

event_store:
  type: sqlite|postgres|file
  config:
    # Type-specific configuration options

worker:
  type: async|thread_pool|process_pool|gevent
  config:
    # Worker-specific configuration options
```

For simpler use cases, consider the basic usage examples in `../01_basic_usage/` or component-based configuration in `../02_component_based_usage/`.