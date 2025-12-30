# Choose File or SQLite Backend

Learn how to select and configure the appropriate storage backend for your use case.

## Overview

OmniQ supports two storage backends:

| Backend | Description | Use Case |
|---------|-------------|-----------|
| **File** | JSON files in a directory | Simple, portable, no dependencies |
| **SQLite** | SQLite database file | Concurrent access, ACID transactions, better performance |

## File Backend

The file backend stores tasks as individual JSON files.

### When to Use File Backend

- **Simple applications**: Low task volume, single worker
- **Development**: Easy inspection and debugging
- **No database**: Don't want SQLite dependency
- **Portability**: Copy directory to backup or migrate

### Advantages

- **Zero dependencies**: Only standard library
- **Transparent**: Tasks are readable JSON files
- **Portable**: Copy entire directory to backup
- **Simple**: Easy to understand implementation

### Disadvantages

- **Performance**: Slower with many tasks (file I/O)
- **Concurrency**: Not optimized for multiple workers
- **No transactions**: Risk of data corruption on crashes
- **Scalability**: Limited by filesystem performance

### Configuration

```python
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

# File backend
settings = Settings(
    backend="file",
    base_dir=Path("./omniq_data"),
    serializer="json"
)
omniq = AsyncOmniQ(settings)
```

### File Structure

```
omniq_data/
├── tasks/
│   ├── task-abc123.json
│   ├── task-def456.json
│   └── ...
├── pending/
├── running/
└── completed/
```

Each task is a JSON file with task metadata.

### Environment Variables

```python
import os

os.environ["OMNIQ_BACKEND"] = "file"
os.environ["OMNIQ_BASE_DIR"] = "./omniq_data"

omniq = AsyncOmniQ.from_env()
```

## SQLite Backend

The SQLite backend uses a SQLite database with proper indexing and ACID transactions.

### When to Use SQLite Backend

- **Production**: Multiple workers, high task volume
- **Concurrency**: Need parallel access to queue
- **Performance**: Optimize for throughput
- **Reliability**: Want transaction safety

### Advantages

- **Performance**: Efficient with many tasks (database indexing)
- **Concurrency**: Multiple workers access safely
- **Transactions**: ACID guarantees prevent corruption
- **Scalability**: Handles high task volumes

### Disadvantages

- **Dependency**: Requires `aiosqlite` package
- **Binary**: Not human-readable without tools
- **Less portable**: Need SQLite client for inspection

### Configuration

```python
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

# SQLite backend
settings = Settings(
    backend="sqlite",
    base_dir=Path("./omniq_data"),
    serializer="json"
)
omniq = AsyncOmniQ(settings)
```

The SQLite database file is created at `{base_dir}/omniq.db`.

### Environment Variables

```python
import os

os.environ["OMNIQ_BACKEND"] = "sqlite"
os.environ["OMNIQ_BASE_DIR"] = "./omniq_data"
os.environ["OMNIQ_DB_PATH"] = "./omniq_data/custom.db"

omniq = AsyncOmniQ.from_env()
```

### Database Schema

The SQLite backend uses these tables:

- `tasks`: Task metadata, status, arguments
- `results`: Task results and errors
- `pending`: Index for pending tasks (optimized dequeue)
- `running`: Index for running tasks (atomic claims)
- `completed`: Index for completed tasks (result lookup)

## Comparison Decision Guide

### Use File Backend If

✅ Single worker application
✅ Development and testing
✅ Low task volume (<1000 tasks)
✅ Need to inspect tasks manually
✅ Want zero external dependencies

### Use SQLite Backend If

✅ Multiple workers (concurrency > 1)
✅ High task volume (>1000 tasks)
✅ Production environment
✅ Need ACID transactions
✅ Performance-critical application

## Performance Comparison

| Metric | File Backend | SQLite Backend |
|--------|--------------|-----------------|
| Small workload (100 tasks) | ~50ms | ~30ms |
| Medium workload (1000 tasks) | ~500ms | ~100ms |
| Large workload (10000 tasks) | ~5s | ~500ms |
| Concurrent workers | Not recommended | Optimized |
| Transaction safety | No | Yes (ACID) |

## Migration: File to SQLite

If you start with file backend and need to migrate to SQLite:

```python
import asyncio
import json
from pathlib import Path
from omniq import AsyncOmniQ
from omniq.config import Settings

async def migrate():
    # Initialize both backends
    file_settings = Settings(
        backend="file",
        base_dir=Path("./file_data")
    )
    sqlite_settings = Settings(
        backend="sqlite",
        base_dir=Path("./sqlite_data")
    )

    file_omniq = AsyncOmniQ(file_settings)
    sqlite_omniq = AsyncOmniQ(sqlite_settings)

    # List all tasks from file backend
    tasks = await file_omniq.list_tasks()

    print(f"Migrating {len(tasks)} tasks...")

    for task in tasks:
        # Re-enqueue to SQLite backend
        task_id = await sqlite_omniq.enqueue(
            task["func_path"],
            task["args"],
            task["kwargs"],
            eta=task.get("eta"),
            interval=task.get("interval"),
            max_retries=task.get("max_retries"),
            timeout=task.get("timeout")
        )

        print(f"Migrated: {task['id']} -> {task_id}")

    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
```

**Note**: This is a simple migration. For production, consider status preservation and error metadata.

## Best Practices

### 1. Start with File Backend

```python
# Development: use file backend
settings = Settings(
    backend="file",
    base_dir=Path("./dev_data")
)
```

### 2. Switch to SQLite for Production

```python
# Production: use SQLite backend
settings = Settings(
    backend="sqlite",
    base_dir=Path("/var/lib/omniq")
)
```

### 3. Use Environment for Flexibility

```python
# Allow switching via environment
os.environ["OMNIQ_BACKEND"] = "file"  # or "sqlite"

omniq = AsyncOmniQ.from_env()
```

### 4. Monitor Storage Performance

```python
# Check storage metrics
import time

start = time.time()
tasks = await omniq.list_tasks()
elapsed = time.time() - start

print(f"Retrieved {len(tasks)} tasks in {elapsed:.3f}s")

if elapsed > 1.0:
    print("Warning: slow storage, consider SQLite backend")
```

## Next Steps

- Learn how to [run workers](run-workers.md) with your chosen backend
- Understand [storage backend tradeoffs](../explanation/storage-tradeoffs.md)
- See [API reference](../reference/api/storage.md) for backend details

## Summary

- **File backend**: Simple, portable, good for development
- **SQLite backend**: Performant, concurrent, good for production
- **Choose based on**: Worker count, task volume, reliability needs
- **Easy migration**: Can switch backends by re-enqueuing tasks

Use file backend for development and simple applications. Switch to SQLite for production, concurrent workers, and high task volumes.
