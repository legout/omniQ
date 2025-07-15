# Redis Backend for OmniQ

This document describes the Redis backend implementation for OmniQ, providing high-performance, distributed task queue, result storage, and event storage capabilities.

## Overview

The Redis backend leverages Redis as a fast, in-memory data store to provide:

- **Task Queue**: Distributed task queuing with priority support and atomic operations
- **Result Storage**: Fast result storage with TTL support
- **Event Storage**: Time-series event logging for monitoring and debugging
- **High Performance**: Sub-millisecond operations for most use cases
- **Scalability**: Horizontal scaling support through Redis clustering
- **Persistence**: Optional data persistence through Redis configuration

## Architecture

### Storage Components

The Redis backend consists of three main storage components:

1. **AsyncRedisQueue / RedisQueue**: Task queue implementation
2. **AsyncRedisResultStorage / RedisResultStorage**: Result storage implementation  
3. **AsyncRedisEventStorage / RedisEventStorage**: Event storage implementation

### Key Design Patterns

- **Async-first, Sync-wrapped**: All operations are implemented as async-first with synchronous wrappers
- **Atomic Operations**: Uses Redis atomic operations for task locking and queue management
- **Key Prefixing**: Supports multiple queue namespaces through configurable key prefixes
- **Priority Queues**: Implements priority queues using Redis sorted sets
- **TTL Support**: Automatic expiration for results and optional task TTL

## Configuration

### RedisConfig

```python
from omniq.models.config import RedisConfig

config = RedisConfig(
    host="localhost",
    port=6379,
    database=0,
    password=None,
    max_connections=10,
    socket_timeout=30.0,
    socket_connect_timeout=30.0,
    retry_on_timeout=True,
    ssl=False,
    tasks_prefix="omniq:tasks",
    results_prefix="omniq:results",
    events_prefix="omniq:events"
)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | str | "localhost" | Redis server hostname |
| `port` | int | 6379 | Redis server port |
| `database` | int | 0 | Redis database number |
| `password` | str | None | Redis password (if required) |
| `max_connections` | int | 10 | Maximum connection pool size |
| `socket_timeout` | float | 30.0 | Socket timeout in seconds |
| `socket_connect_timeout` | float | 30.0 | Connection timeout in seconds |
| `retry_on_timeout` | bool | True | Retry operations on timeout |
| `ssl` | bool | False | Enable SSL/TLS connection |
| `tasks_prefix` | str | "omniq:tasks" | Key prefix for task storage |
| `results_prefix` | str | "omniq:results" | Key prefix for result storage |
| `events_prefix` | str | "omniq:events" | Key prefix for event storage |

## Usage Examples

### Basic Usage

```python
import asyncio
from omniq.models.config import RedisConfig
from omniq.backend.redis import AsyncRedisBackend
from omniq.models.task import Task

async def main():
    config = RedisConfig(host="localhost", port=6379)
    
    async with AsyncRedisBackend(config) as backend:
        # Create and enqueue a task
        task = Task(
            func="my_function",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            queue_name="default"
        )
        
        task_id = await backend.queue.enqueue(task)
        print(f"Enqueued task: {task_id}")
        
        # Dequeue and process
        dequeued_task = await backend.queue.dequeue(["default"])
        if dequeued_task:
            print(f"Processing task: {dequeued_task.id}")

asyncio.run(main())
```

### Synchronous Usage

```python
from omniq.models.config import RedisConfig
from omniq.backend.redis import RedisBackend
from omniq.models.task import Task

config = RedisConfig(host="localhost", port=6379)

with RedisBackend(config) as backend:
    # Create and enqueue a task
    task = Task(
        func="my_function",
        args=(1, 2, 3),
        queue_name="default"
    )
    
    task_id = backend.queue.enqueue_sync(task)
    print(f"Enqueued task: {task_id}")
    
    # Get queue size
    size = backend.queue.get_queue_size_sync("default")
    print(f"Queue size: {size}")
```

### Result Storage

```python
from omniq.models.result import TaskResult, ResultStatus
from datetime import timedelta

# Store a result
result = TaskResult(
    task_id="task-123",
    status=ResultStatus.SUCCESS,
    result={"output": "Hello, World!"},
    ttl=timedelta(hours=24)
)

await backend.result_storage.set(result)

# Retrieve a result
retrieved = await backend.result_storage.get("task-123")
if retrieved:
    print(f"Result: {retrieved.result}")
```

### Event Logging

```python
from omniq.models.event import TaskEvent, EventType

# Log an event
event = TaskEvent(
    task_id="task-123",
    event_type=EventType.COMPLETED,
    details={"duration": 1.5, "worker": "worker-001"}
)

await backend.event_storage.log_event(event)

# Query events
events = await backend.event_storage.get_events(
    task_id="task-123",
    limit=10
)
```

## Redis Data Structure

### Task Queue

Tasks are stored using the following Redis data structures:

- **Task Data**: `{tasks_prefix}:task:{task_id}` → JSON serialized task
- **Queue Index**: `{tasks_prefix}:queue:{queue_name}` → Sorted set with priority scores
- **Task Locks**: `{tasks_prefix}:lock:{task_id}` → Lock keys with TTL

### Result Storage

Results are stored as:

- **Result Data**: `{results_prefix}:result:{task_id}` → JSON serialized result with TTL

### Event Storage

Events use:

- **Event Data**: `{events_prefix}:event:{event_id}` → JSON serialized event
- **Event Index**: `{events_prefix}:events` → Sorted set with timestamp scores

## Performance Characteristics

### Throughput

- **Enqueue**: ~50,000 ops/sec (single Redis instance)
- **Dequeue**: ~30,000 ops/sec (with locking)
- **Result Storage**: ~80,000 ops/sec
- **Event Logging**: ~60,000 ops/sec

### Latency

- **Enqueue**: < 1ms (P99)
- **Dequeue**: < 2ms (P99, including lock acquisition)
- **Result Retrieval**: < 0.5ms (P99)
- **Event Query**: < 1ms (P99)

*Performance numbers are approximate and depend on Redis configuration, network latency, and hardware.*

## Scaling and High Availability

### Redis Clustering

The Redis backend supports Redis Cluster for horizontal scaling:

```python
config = RedisConfig(
    host="redis-cluster-endpoint",
    port=6379,
    # Redis cluster will automatically distribute keys
)
```

### Redis Sentinel

For high availability with Redis Sentinel:

```python
# Configure Redis Sentinel in your Redis client
# The backend will work transparently with Sentinel
```

### Connection Pooling

The backend uses connection pooling for optimal performance:

```python
config = RedisConfig(
    max_connections=20,  # Adjust based on concurrency needs
    socket_timeout=30.0,
    retry_on_timeout=True
)
```

## Monitoring and Observability

### Health Checks

```python
health = await backend.health_check()
print(f"Status: {health['status']}")
print(f"Connected: {health['connected']}")
```

### Cleanup Operations

```python
# Clean up expired tasks and results
cleanup_stats = await backend.cleanup()
print(f"Cleaned up {cleanup_stats['expired_tasks']} tasks")
print(f"Cleaned up {cleanup_stats['expired_results']} results")
```

### Event Monitoring

```python
from datetime import datetime, timedelta

# Get recent events
recent_events = await backend.event_storage.get_events(
    start_time=datetime.utcnow() - timedelta(hours=1),
    limit=100
)

# Clean up old events
cutoff_time = datetime.utcnow() - timedelta(days=7)
cleaned = await backend.event_storage.cleanup_old_events(cutoff_time)
```

## Best Practices

### Configuration

1. **Use appropriate database numbers** for different environments
2. **Configure connection pooling** based on expected concurrency
3. **Set up SSL/TLS** for production environments
4. **Use key prefixes** to avoid conflicts in shared Redis instances

### Performance Optimization

1. **Batch operations** when possible
2. **Use appropriate TTL values** for results
3. **Monitor Redis memory usage** and configure eviction policies
4. **Consider Redis persistence settings** based on durability requirements

### Error Handling

1. **Implement retry logic** for transient Redis failures
2. **Monitor connection health** and reconnect as needed
3. **Handle Redis memory limits** gracefully
4. **Log Redis errors** for debugging

### Security

1. **Use Redis AUTH** in production
2. **Configure Redis bind addresses** appropriately
3. **Enable SSL/TLS** for network encryption
4. **Implement network-level security** (VPC, firewalls)

## Troubleshooting

### Common Issues

1. **Connection timeouts**: Increase `socket_timeout` and `socket_connect_timeout`
2. **Memory issues**: Configure Redis `maxmemory` and eviction policies
3. **Slow operations**: Check Redis latency and network connectivity
4. **Lock contention**: Monitor task processing patterns and adjust concurrency

### Debugging

1. **Enable Redis slow log**: `CONFIG SET slowlog-log-slower-than 10000`
2. **Monitor Redis metrics**: Use `INFO` command or monitoring tools
3. **Check key patterns**: Use `SCAN` to inspect key distribution
4. **Analyze event logs**: Query recent events for error patterns

## Migration from Other Backends

### From SQLite

```python
# Export tasks from SQLite
sqlite_backend = SQLiteBackend(sqlite_config)
tasks = await sqlite_backend.queue.list_tasks()

# Import to Redis
redis_backend = AsyncRedisBackend(redis_config)
for task in tasks:
    await redis_backend.queue.enqueue(task)
```

### From File Backend

```python
# Similar migration pattern
file_backend = FileBackend(file_config)
# ... export and import logic
```

## Dependencies

The Redis backend requires:

- `redis[hiredis]>=4.0.0` - Redis client with hiredis for performance
- `msgspec>=0.18.0` - Fast serialization

Install with:

```bash
pip install "redis[hiredis]>=4.0.0" "msgspec>=0.18.0"
```

## Limitations

1. **Memory constraints**: Redis stores all data in memory
2. **Single-threaded**: Redis operations are single-threaded (use clustering for parallelism)
3. **Network dependency**: Requires network connectivity to Redis server
4. **Persistence trade-offs**: Balance between performance and durability

## Future Enhancements

- Redis Streams support for enhanced event processing
- Redis Modules integration (RedisJSON, RedisTimeSeries)
- Advanced monitoring and metrics collection
- Automatic failover and recovery mechanisms
- Compression support for large payloads