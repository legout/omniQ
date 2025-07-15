# PostgreSQL Backend for OmniQ

The PostgreSQL backend provides a robust, scalable, and ACID-compliant storage solution for OmniQ, supporting all core functionality including task queues, result storage, event logging, and scheduling.

## Features

- **ACID Compliance**: Full transaction support with row-level locking
- **High Performance**: Connection pooling with asyncpg for optimal performance
- **Scalability**: Supports multiple workers and concurrent operations
- **Advanced Querying**: Rich filtering and pagination capabilities
- **Schema Management**: Automatic schema creation and indexing
- **Async/Sync Support**: Both async and sync interfaces available

## Installation

Install the required PostgreSQL driver:

```bash
pip install asyncpg
```

## Quick Start

### Async Usage

```python
import asyncio
from omniq.backend.postgres import create_async_postgres_backend
from omniq.models.task import Task

async def main():
    backend = create_async_postgres_backend(
        host="localhost",
        port=5432,
        database="omniq",
        username="postgres",
        password="password"
    )
    
    async with backend:
        # Create and enqueue a task
        task = Task(
            func="mymodule.my_function",
            args=(1, 2, 3),
            queue_name="default"
        )
        
        await backend.task_queue.enqueue(task)
        
        # Dequeue and process
        dequeued = await backend.task_queue.dequeue(["default"])
        if dequeued:
            print(f"Processing task: {dequeued.id}")

asyncio.run(main())
```

### Sync Usage

```python
from omniq.backend.postgres import create_postgres_backend
from omniq.models.task import Task

backend = create_postgres_backend(
    host="localhost",
    port=5432,
    database="omniq",
    username="postgres",
    password="password"
)

with backend:
    # Create and enqueue a task
    task = Task(
        func="mymodule.my_function",
        args=(1, 2, 3),
        queue_name="default"
    )
    
    backend.task_queue.enqueue_sync(task)
    
    # Dequeue and process
    dequeued = backend.task_queue.dequeue_sync(["default"])
    if dequeued:
        print(f"Processing task: {dequeued.id}")
```

## Configuration

### PostgresConfig

```python
from omniq.models.config import PostgresConfig
from omniq.backend.postgres import PostgreSQLBackend

config = PostgresConfig(
    host="localhost",
    port=5432,
    database="omniq",
    username="postgres",
    password="password",
    min_connections=1,
    max_connections=10,
    command_timeout=60.0,
    schema="public",
    tasks_table="tasks",
    results_table="results",
    events_table="events",
    schedules_table="schedules"
)

backend = PostgreSQLBackend(config)
```

### Connection Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | str | "localhost" | PostgreSQL server host |
| `port` | int | 5432 | PostgreSQL server port |
| `database` | str | "omniq" | Database name |
| `username` | str | "postgres" | Database username |
| `password` | str | "" | Database password |
| `min_connections` | int | 1 | Minimum pool connections |
| `max_connections` | int | 10 | Maximum pool connections |
| `command_timeout` | float | 60.0 | Command timeout in seconds |
| `schema` | str | "public" | Database schema |

### Table Names

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tasks_table` | "tasks" | Task queue table name |
| `results_table` | "results" | Results storage table name |
| `events_table` | "events" | Event logging table name |
| `schedules_table` | "schedules" | Schedule storage table name |

## Database Schema

The PostgreSQL backend automatically creates the following tables:

### Tasks Table

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    func TEXT NOT NULL,
    args JSONB NOT NULL,
    kwargs JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    run_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_delay REAL NOT NULL DEFAULT 1.0,
    dependencies JSONB NOT NULL DEFAULT '[]',
    callbacks JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    task_data JSONB NOT NULL
);
```

### Results Table

```sql
CREATE TABLE results (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',
    result JSONB,
    error TEXT,
    error_type TEXT,
    traceback TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    worker_id TEXT,
    execution_time REAL,
    memory_usage BIGINT,
    metadata JSONB NOT NULL DEFAULT '{}',
    result_data JSONB NOT NULL
);
```

### Events Table

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    message TEXT,
    details JSONB NOT NULL DEFAULT '{}',
    worker_id TEXT,
    queue_name TEXT,
    schedule_id TEXT,
    error_type TEXT,
    error_message TEXT,
    traceback TEXT,
    execution_time REAL,
    memory_usage BIGINT,
    metadata JSONB NOT NULL DEFAULT '{}',
    event_data JSONB NOT NULL
);
```

### Schedules Table

```sql
CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    schedule_type TEXT NOT NULL,
    func TEXT NOT NULL,
    args JSONB NOT NULL DEFAULT '[]',
    kwargs JSONB NOT NULL DEFAULT '{}',
    queue_name TEXT NOT NULL DEFAULT 'default',
    cron_expression TEXT,
    interval_seconds REAL,
    timestamp TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    max_runs INTEGER,
    run_count INTEGER NOT NULL DEFAULT 0,
    ttl_seconds REAL,
    expires_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    schedule_data JSONB NOT NULL
);
```

## Storage Components

### Task Queue (`AsyncPostgresQueue` / `PostgresQueue`)

```python
# Async
await backend.task_queue.enqueue(task)
task = await backend.task_queue.dequeue(["queue1", "queue2"])
await backend.task_queue.update_task(task)
tasks = await backend.task_queue.list_tasks(queue_name="default", limit=10)

# Sync
backend.task_queue.enqueue_sync(task)
task = backend.task_queue.dequeue_sync(["queue1", "queue2"])
backend.task_queue.update_task_sync(task)
tasks = backend.task_queue.list_tasks_sync(queue_name="default", limit=10)
```

### Result Storage (`AsyncPostgresResultStorage` / `PostgresResultStorage`)

```python
# Async
await backend.result_storage.set(result)
result = await backend.result_storage.get(task_id)
results = await backend.result_storage.list_results(status="success", limit=10)

# Sync
backend.result_storage.set_sync(result)
result = backend.result_storage.get_sync(task_id)
results = backend.result_storage.list_results_sync(status="success", limit=10)
```

### Event Storage (`AsyncPostgresEventStorage` / `PostgresEventStorage`)

```python
# Async
await backend.event_storage.log_event(event)
events = await backend.event_storage.get_events(task_id=task_id, limit=10)

# Sync
backend.event_storage.log_event_sync(event)
events = backend.event_storage.get_events_sync(task_id=task_id, limit=10)
```

### Schedule Storage (`AsyncPostgresScheduleStorage` / `PostgresScheduleStorage`)

```python
# Async
await backend.schedule_storage.save_schedule(schedule)
schedule = await backend.schedule_storage.get_schedule(schedule_id)
ready_schedules = await backend.schedule_storage.get_ready_schedules()

# Sync
backend.schedule_storage.save_schedule_sync(schedule)
schedule = backend.schedule_storage.get_schedule_sync(schedule_id)
ready_schedules = backend.schedule_storage.get_ready_schedules_sync()
```

## Advanced Features

### Row-Level Locking

The PostgreSQL backend uses `FOR UPDATE SKIP LOCKED` for safe concurrent task dequeuing:

```sql
SELECT id FROM tasks
WHERE queue_name = ANY($1::text[])
AND status = 'pending'
AND (run_at IS NULL OR run_at <= $2)
AND (expires_at IS NULL OR expires_at > $2)
ORDER BY priority DESC, created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1
```

### Connection Pooling

Automatic connection pooling with configurable min/max connections:

```python
backend = create_postgres_backend(
    min_connections=5,
    max_connections=20,
    command_timeout=30.0
)
```

### Schema Isolation

Use different schemas for different environments:

```python
# Development
dev_backend = create_postgres_backend(schema="omniq_dev")

# Production
prod_backend = create_postgres_backend(schema="omniq_prod")
```

### Performance Optimization

The backend includes optimized indexes for common queries:

- Task queue priority and status
- Result completion times
- Event timestamps and types
- Schedule next run times

## Error Handling

```python
from omniq.backend.postgres import create_postgres_backend
import asyncpg

try:
    backend = create_postgres_backend(
        host="localhost",
        database="omniq"
    )
    
    with backend:
        # Your operations here
        pass
        
except asyncpg.ConnectionError as e:
    print(f"Database connection failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Migration and Maintenance

### Cleanup Operations

```python
# Clean up expired tasks
expired_count = await backend.task_queue.cleanup_expired_tasks()

# Clean up expired results
expired_results = await backend.result_storage.cleanup_expired_results()

# Clean up old events
from datetime import datetime, timedelta
cutoff = datetime.utcnow() - timedelta(days=30)
old_events = await backend.event_storage.cleanup_old_events(cutoff)

# Clean up expired schedules
expired_schedules = await backend.schedule_storage.cleanup_expired_schedules()
```

### Monitoring

```python
# Get queue sizes
queue_size = await backend.task_queue.get_queue_size("default")

# List recent events
recent_events = await backend.event_storage.get_events(
    limit=100,
    offset=0
)

# Get ready schedules
ready = await backend.schedule_storage.get_ready_schedules()
```

## Best Practices

1. **Use Connection Pooling**: Configure appropriate min/max connections
2. **Schema Isolation**: Use different schemas for different environments
3. **Regular Cleanup**: Implement cleanup jobs for expired data
4. **Monitoring**: Monitor queue sizes and event logs
5. **Indexing**: The backend creates optimal indexes automatically
6. **Error Handling**: Always handle connection and query errors
7. **Context Managers**: Use `async with` or `with` for automatic cleanup

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check PostgreSQL server is running
2. **Authentication Failed**: Verify username/password
3. **Database Not Found**: Create the database first
4. **Permission Denied**: Ensure user has CREATE privileges
5. **Pool Exhausted**: Increase max_connections or reduce usage

### Debug Logging

Enable PostgreSQL query logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- **Connection Pooling**: Reuse connections for better performance
- **Batch Operations**: Use transactions for multiple operations
- **Indexing**: Indexes are created automatically for optimal performance
- **JSONB**: Structured data stored efficiently as JSONB
- **Prepared Statements**: asyncpg uses prepared statements automatically

## Comparison with SQLite Backend

| Feature | PostgreSQL | SQLite |
|---------|------------|--------|
| Concurrency | Excellent | Limited |
| Scalability | High | Low |
| ACID | Full | Full |
| Setup | Requires server | File-based |
| Performance | High | Good |
| Features | Advanced | Basic |

The PostgreSQL backend is recommended for production deployments requiring high concurrency and scalability.