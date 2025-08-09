# Backend-Based Usage Examples

This directory contains examples demonstrating the backend-based approach to using the OmniQ library, where backends act as unified factories for creating storage components.

## Files

- **`backend_usage.py`**: Demonstrates backend-based usage with single and mixed backend configurations
- **`backend_usage.ipynb`**: Jupyter notebook containing the same examples with detailed explanations about backend abstraction

## Overview

The backend-based approach simplifies OmniQ configuration by providing unified interfaces for storage systems. Instead of configuring each component individually, you create backend instances that act as factories for all related storage components.

## Backend Architecture

Backends provide a unified interface for storage systems:

- **Single Backend**: Use one backend type for all components (queue, result storage, event storage)
- **Mixed Backends**: Use different backend types for different components based on your needs
- **Simplified Configuration**: Configure storage once at the backend level rather than per component
- **Consistent Settings**: Ensure all components from the same backend share consistent configuration

## Available Backends

- **SQLiteBackend**: File-based SQLite database for all storage needs
- **FileBackend**: File system storage using fsspec (supports local, S3, Azure, GCP)
- **PostgresBackend**: PostgreSQL database for scalable, distributed storage
- **RedisBackend**: Redis for high-performance caching and queuing
- **NATSBackend**: NATS messaging system for distributed task processing

## Benefits

### Single Backend Approach

- **Simplicity**: One configuration for all storage components
- **Consistency**: All components use the same storage system and settings
- **Easy Setup**: Minimal configuration required to get started
- **Resource Efficiency**: Shared connections and resources across components

### Mixed Backend Approach

- **Optimization**: Choose the best backend for each component's specific needs
- **Performance**: Use fast backends for queues, persistent backends for results
- **Scalability**: Scale different components independently
- **Flexibility**: Adapt to existing infrastructure and requirements

## When to Use Backend-Based Approach

Use this approach when you want:

- **Simplified Configuration**: Reduce boilerplate code and configuration complexity
- **Unified Storage**: Keep all data in the same storage system for consistency
- **Quick Setup**: Get started quickly with minimal configuration
- **Backend Optimization**: Leverage backend-specific optimizations and features
- **Mixed Requirements**: Use different backends for different components based on performance needs

## Configuration Patterns

### Single Backend Pattern
```python
# All components use the same backend
backend = SQLiteBackend({"db_path": "omniq.db"})
oq = OmniQ.from_backend(backend, worker_type="thread_pool")
```

### Mixed Backend Pattern
```python
# Different backends for different components
file_backend = FileBackend({"base_dir": "/tmp/omniq"})
sqlite_backend = SQLiteBackend({"db_path": "results.db"})
postgres_backend = PostgresBackend({"host": "localhost", "database": "events"})

oq = OmniQ.from_backend(
    backend=file_backend,           # For task queue
    result_store_backend=sqlite_backend,  # For result storage
    event_store_backend=postgres_backend  # For event storage
)
```

### Component Creation Pattern
```python
# Create individual components from backends
backend = SQLiteBackend({"db_path": "omniq.db"})
task_queue = TaskQueue.from_backend(backend, queues=["high", "medium", "low"])
result_store = ResultStore.from_backend(backend)
event_store = EventStore.from_backend(backend)
```

## Comparison with Other Approaches

| Approach | Configuration Complexity | Flexibility | Use Case |
|----------|-------------------------|-------------|----------|
| **Basic Usage** | Low | Low | Simple applications, getting started |
| **Component-Based** | High | Very High | Complex systems, maximum control |
| **Backend-Based** | Medium | High | Production systems, balanced approach |

The backend-based approach strikes a balance between simplicity and flexibility, making it ideal for most production use cases where you need some customization but don't want to manage every component individually.