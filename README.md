# OmniQ - A Flexible Task Queue Library for Python

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods.

## Features

- **Async-first design** with sync wrapper support
- **Multiple storage backends** (SQLite and Azure Blob Storage implemented, PostgreSQL/Redis/NATS planned)
- **Task scheduling** with delays and TTL support
- **Retry mechanisms** with exponential backoff
- **Event logging** for task lifecycle monitoring
- **Decorator-based task registration**
- **Context manager support** for resource management
- **Type-safe models** using msgspec for serialization

## Installation

```bash
pip install -e .
```

## Quick Start

### Basic Usage

```python
import asyncio
from omniq import OmniQ

async def main():
    # Initialize OmniQ with SQLite backend (default)
    async with OmniQ() as omniq:
        # Submit a task
        task_id = await omniq.submit_task(
            func_name="my_function",
            args=(10, 20),
            queue="default",
            priority=1
        )
        
        # Get task information
        task = await omniq.get_task(task_id)
        print(f"Task {task.id}: {task.func}{task.args} [{task.status}]")
        
        # Get task events
        events = await omniq.get_task_events(task_id)
        for event in events:
            print(f"{event.timestamp}: {event.event_type}")

asyncio.run(main())
```

### Synchronous Usage

```python
from omniq import OmniQ

# Use synchronous methods
with OmniQ() as omniq:
    task_id = omniq.submit_task_sync(
        func_name="my_function",
        args=(10, 20)
    )
    
    task = omniq.get_task_sync(task_id)
    print(f"Task: {task.func}{task.args}")
```

### Task Decorator

```python
from omniq import OmniQ

omniq = OmniQ()

@omniq.task(name="add", queue="math", priority=2)
def add_numbers(a: int, b: int) -> int:
    return a + b

async def main():
    async with omniq:
        # Submit task using decorator
        task_id = await add_numbers.submit(5, 10)
        print(f"Task submitted: {task_id}")

asyncio.run(main())
```

### Advanced Features

```python
from datetime import timedelta
from omniq import OmniQ

async def main():
    async with OmniQ() as omniq:
        # Task with delay
        task_id = await omniq.submit_task(
            func_name="delayed_task",
            delay=timedelta(minutes=5)
        )
        
        # Task with TTL
        task_id = await omniq.submit_task(
            func_name="expiring_task",
            ttl=timedelta(hours=1)
        )
        
        # Task with retries
        task_id = await omniq.submit_task(
            func_name="unreliable_task",
            retry_attempts=3,
            retry_delay=timedelta(seconds=2)
        )
        
        # List tasks by queue
        tasks = await omniq.get_tasks_by_queue("default", limit=10)
        
        # Cleanup expired tasks
        stats = await omniq.cleanup_expired()
        print(f"Cleaned up: {stats}")

asyncio.run(main())
```

### Azure Backend Usage

```python
import os
from omniq.backend.azure import AzureBackend

# Create Azure backend with connection string
backend = AzureBackend(
    container_name="omniq-prod",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)

async def main():
    async with backend:
        # Get storage instances
        task_queue = backend.async_task_storage
        result_storage = backend.async_result_storage
        
        # Use like any other backend
        task_id = await task_queue.enqueue(task)
        result = await result_storage.get(task_id)

asyncio.run(main())
```

For detailed Azure backend documentation, see [`docs/azure_backend.md`](docs/azure_backend.md).

## Architecture

### Core Components

- **OmniQ**: Main orchestrator class providing the user-facing API
- **Task**: Core task model with metadata and lifecycle management
- **TaskResult**: Result storage model for completed tasks
- **TaskEvent**: Event logging model for task lifecycle tracking
- **Schedule**: Scheduling model for recurring tasks

### Storage Backends

- **SQLiteBackend**: File-based SQLite storage (implemented)
- **AzureBackend**: Azure Blob Storage backend (implemented)
- **PostgresBackend**: PostgreSQL storage (planned)
- **RedisBackend**: Redis storage (planned)
- **NATSBackend**: NATS streaming storage (planned)

### Storage Interfaces

- **BaseTaskQueue**: Abstract interface for task queue operations
- **BaseResultStorage**: Abstract interface for result storage
- **BaseEventStorage**: Abstract interface for event logging
- **BaseScheduleStorage**: Abstract interface for schedule management

## Configuration

### Environment Variables

All configuration can be set via environment variables with the `OMNIQ_` prefix:

```bash
export OMNIQ_LOG_LEVEL=DEBUG
export OMNIQ_TASK_TIMEOUT=300
export OMNIQ_MAX_WORKERS=10
```

### Programmatic Configuration

```python
from omniq import OmniQ
from omniq.models.config import SQLiteConfig, OmniQConfig

# SQLite configuration
sqlite_config = SQLiteConfig(
    database_path="./my_tasks.db",
    timeout=30.0,
    journal_mode="WAL"
)

# Main configuration
config = OmniQConfig(
    project_name="my_project",
    default_queue="tasks",
    log_level="INFO"
)

omniq = OmniQ(config=config)
```

## Development Status

### ✅ Completed

- Core data models (Task, TaskResult, TaskEvent, Schedule)
- Abstract storage interfaces
- SQLite backend implementation
- Azure Blob Storage backend implementation
- Main OmniQ orchestrator class
- Basic task submission and retrieval
- Event logging system
- Configuration management
- Context manager support
- Task decorator functionality

### 🚧 In Progress

- Worker implementation for task execution
- Serialization utilities
- Comprehensive testing

### 📋 Planned

- Additional storage backends (PostgreSQL, Redis, NATS)
- Worker pools and execution engines
- Web UI for monitoring
- Metrics and monitoring
- Distributed task execution
- Task dependencies
- Workflow orchestration

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run the basic example:

```bash
python examples/basic_usage.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Roadmap

### Phase 1: Core Foundation ✅
- Basic task queue operations
- SQLite backend
- Event logging
- Configuration system

### Phase 2: Worker Implementation 🚧
- Task execution engine
- Worker pools
- Error handling and retries

### Phase 3: Advanced Features 📋
- Additional backends
- Distributed execution
- Web monitoring interface
- Performance optimizations

### Phase 4: Enterprise Features 📋
- High availability
- Clustering support
- Advanced monitoring
- Security features