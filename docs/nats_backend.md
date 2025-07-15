# NATS Storage Backend for OmniQ

This document describes the NATS-based storage backend implementation for OmniQ, providing distributed messaging and persistent storage using NATS JetStream.

## Overview

The NATS backend provides a complete storage solution for OmniQ using NATS JetStream for distributed messaging and NATS Key-Value store for persistent data storage. It implements all required storage interfaces:

- **Task Queue**: Distributed task queuing with priority support
- **Result Storage**: Persistent task result storage with TTL
- **Event Storage**: Task lifecycle event logging
- **Schedule Storage**: Persistent schedule management

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Task Queue    │    │ Result Storage  │    │ Event Storage   │
│  (JetStream)    │    │   (NATS KV)     │    │  (JetStream)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────┐     │     ┌─────────────────┐
         │Schedule Storage │     │     │   NATS Server   │
         │   (NATS KV)     │     │     │   (JetStream)   │
         └─────────────────┘     │     └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │  NATSBackend    │
                    │   (Unified)     │
                    └─────────────────┘
```

## Components

### AsyncNATSQueue

Implements distributed task queuing using NATS JetStream:

- **Subjects**: `omniq.tasks.{queue_name}.{task_id}`
- **Stream**: `OMNIQ_TASKS` with work queue retention
- **Features**: Priority ordering, queue groups, distributed processing
- **Limitations**: No direct task lookup or update (append-only)

### AsyncNATSResultStorage

Implements result storage using NATS Key-Value store:

- **Bucket**: `omniq_results`
- **TTL**: 7 days (configurable)
- **Features**: Fast key-value access, automatic expiration
- **Operations**: Get, set, delete, list with filtering

### AsyncNATSEventStorage

Implements event logging using NATS JetStream:

- **Subjects**: `omniq.events.{event_type}.{task_id}`
- **Stream**: `OMNIQ_EVENTS` with limits retention
- **Features**: Structured event logging, automatic cleanup
- **Retention**: 30 days, 10M messages max

### AsyncNATSScheduleStorage

Implements schedule management using NATS Key-Value store:

- **Bucket**: `omniq_schedules`
- **TTL**: None (persistent)
- **Features**: Schedule CRUD operations, ready schedule queries
- **Operations**: Save, get, update, delete, list, get ready schedules

## Configuration

```python
config = {
    # Connection settings
    "servers": ["nats://localhost:4222"],
    "user": "username",           # Optional
    "password": "password",       # Optional
    "token": "auth_token",        # Optional
    
    # TLS settings
    "tls": True,                  # Optional
    "tls_cert": "/path/to/cert",  # Optional
    "tls_key": "/path/to/key",    # Optional
    "tls_ca": "/path/to/ca",      # Optional
    
    # Connection tuning
    "connect_timeout": 2.0,
    "reconnect_time_wait": 2.0,
    "max_reconnect_attempts": 60,
    
    # Subject configuration
    "tasks_subject": "omniq.tasks",
    "results_subject": "omniq.results",
    "events_subject": "omniq.events",
    "schedules_subject": "omniq.schedules",
    
    # Queue configuration
    "queue_group": "omniq_workers",
}
```

## Usage Examples

### Basic Usage

```python
from omniq.storage.nats import create_nats_backend

# Create backend
config = {"servers": ["nats://localhost:4222"]}
backend = create_nats_backend(config)

# Async usage
async with backend.async_context():
    # Enqueue task
    task = Task(id="task1", func="my_function")
    await backend.task_queue.enqueue(task)
    
    # Store result
    result = TaskResult(task_id="task1", result="success")
    await backend.result_storage.set(result)
    
    # Log event
    event = TaskEvent(task_id="task1", event_type=EventType.COMPLETED)
    await backend.event_storage.log_event(event)

# Sync usage
with backend:
    task = Task(id="task2", func="my_function")
    backend.sync_task_queue.enqueue_sync(task)
```

### Individual Components

```python
from omniq.storage.nats import AsyncNATSQueue, AsyncNATSResultStorage

# Task queue only
queue = AsyncNATSQueue(servers=["nats://localhost:4222"])
async with queue:
    task_id = await queue.enqueue(task)
    next_task = await queue.dequeue(["default"])

# Result storage only
storage = AsyncNATSResultStorage(servers=["nats://localhost:4222"])
async with storage:
    await storage.set(result)
    retrieved = await storage.get(task_id)
```

### Schedule Management

```python
from omniq.models.schedule import Schedule

# Create cron schedule
schedule = Schedule.from_cron(
    cron_expression="0 */5 * * *",  # Every 5 minutes
    func="scheduled_task",
    args=("arg1",),
    queue_name="scheduled"
)

# Save and manage
async with backend.async_context():
    await backend.schedule_storage.save_schedule(schedule)
    
    # Get ready schedules
    ready = await backend.schedule_storage.get_ready_schedules()
    
    # Update schedule
    schedule.pause()
    await backend.schedule_storage.update_schedule(schedule)
```

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  nats:
    image: nats:latest
    ports:
      - "4222:4222"
      - "8222:8222"  # HTTP monitoring
    command: [
      "--jetstream",
      "--store_dir=/data",
      "--http_port=8222"
    ]
    volumes:
      - nats_data:/data

  omniq_worker:
    image: omniq:latest
    depends_on:
      - nats
    environment:
      - OMNIQ_BACKEND=nats
      - NATS_SERVERS=nats://nats:4222
    volumes:
      - ./config.yaml:/app/config.yaml

volumes:
  nats_data:
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nats-jetstream
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nats
  template:
    metadata:
      labels:
        app: nats
    spec:
      containers:
      - name: nats
        image: nats:latest
        args:
        - "--jetstream"
        - "--cluster_name=omniq"
        - "--cluster=nats://0.0.0.0:6222"
        - "--routes=nats://nats-0.nats:6222,nats://nats-1.nats:6222,nats://nats-2.nats:6222"
        ports:
        - containerPort: 4222
        - containerPort: 6222
        - containerPort: 8222
        volumeMounts:
        - name: nats-storage
          mountPath: /data
      volumes:
      - name: nats-storage
        persistentVolumeClaim:
          claimName: nats-storage-pvc
```

## Performance Considerations

### Throughput

- **Task Queue**: ~100K tasks/sec (depends on message size)
- **Result Storage**: ~50K operations/sec (KV store)
- **Event Logging**: ~200K events/sec (append-only)
- **Schedule Storage**: ~10K operations/sec (KV store)

### Scaling

- **Horizontal**: Multiple NATS servers in cluster
- **Vertical**: Increase JetStream memory/disk limits
- **Partitioning**: Use multiple subjects for load distribution

### Tuning

```python
# High-throughput configuration
config = {
    "servers": ["nats://node1:4222", "nats://node2:4222", "nats://node3:4222"],
    "connect_timeout": 5.0,
    "reconnect_time_wait": 1.0,
    "max_reconnect_attempts": 100,
    
    # Use separate subjects for different priorities
    "tasks_subject": "omniq.tasks.high",  # High priority
    # "tasks_subject": "omniq.tasks.low",   # Low priority
}
```

## Monitoring

### NATS Monitoring

```bash
# Stream info
nats stream info OMNIQ_TASKS

# Consumer info
nats consumer info OMNIQ_TASKS omniq_workers

# Key-Value bucket info
nats kv info omniq_results
```

### Metrics

- **Stream Messages**: Total messages in streams
- **Consumer Lag**: Unprocessed messages per consumer
- **KV Operations**: Get/Set/Delete rates
- **Connection Health**: Active connections, reconnects

## Limitations

1. **Task Updates**: NATS JetStream is append-only, task updates not supported
2. **Complex Queries**: Limited querying capabilities compared to SQL databases
3. **Message Size**: Default 1MB limit per message
4. **Ordering**: No global ordering across subjects
5. **Transactions**: No multi-operation transactions

## Migration

### From Redis

```python
# Redis to NATS migration script
async def migrate_redis_to_nats():
    redis_backend = create_redis_backend(redis_config)
    nats_backend = create_nats_backend(nats_config)
    
    async with redis_backend.async_context(), nats_backend.async_context():
        # Migrate tasks
        tasks = await redis_backend.task_queue.list_tasks()
        for task in tasks:
            await nats_backend.task_queue.enqueue(task)
        
        # Migrate results
        results = await redis_backend.result_storage.list_results()
        for result in results:
            await nats_backend.result_storage.set(result)
        
        # Migrate schedules
        schedules = await redis_backend.schedule_storage.list_schedules()
        for schedule in schedules:
            await nats_backend.schedule_storage.save_schedule(schedule)
```

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Check NATS server status
   - Verify network connectivity
   - Check authentication credentials

2. **JetStream Not Enabled**
   - Start NATS with `--jetstream` flag
   - Check JetStream configuration

3. **Stream Creation Errors**
   - Verify JetStream permissions
   - Check stream name conflicts
   - Review resource limits

4. **Performance Issues**
   - Monitor stream lag
   - Check message sizes
   - Review retention policies

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable NATS client debugging
config = {
    "servers": ["nats://localhost:4222"],
    "verbose": True,
    "pedantic": True,
}
```

## Security

### Authentication

```python
# User/Password
config = {
    "servers": ["nats://localhost:4222"],
    "user": "omniq_user",
    "password": "secure_password"
}

# Token-based
config = {
    "servers": ["nats://localhost:4222"],
    "token": "jwt_token_here"
}
```

### TLS

```python
config = {
    "servers": ["nats://localhost:4222"],
    "tls": True,
    "tls_cert": "/path/to/client.crt",
    "tls_key": "/path/to/client.key",
    "tls_ca": "/path/to/ca.crt"
}
```

### Permissions

```json
{
  "users": [
    {
      "user": "omniq_worker",
      "password": "worker_pass",
      "permissions": {
        "publish": ["omniq.tasks.>", "omniq.events.>"],
        "subscribe": ["omniq.tasks.>"],
        "allow_responses": true
      }
    }
  ]
}
```

## Best Practices

1. **Use Queue Groups**: Ensure load balancing across workers
2. **Monitor Stream Lag**: Set up alerts for consumer lag
3. **Set Appropriate TTLs**: Balance storage costs with data retention needs
4. **Use Clustering**: Deploy NATS in cluster mode for high availability
5. **Separate Subjects**: Use different subjects for different priorities/types
6. **Regular Backups**: Backup JetStream data directory
7. **Resource Limits**: Set appropriate memory and disk limits
8. **Connection Pooling**: Reuse connections where possible

## Future Enhancements

1. **Improved Querying**: Add support for complex event queries
2. **Task Updates**: Implement task update mechanism using KV store
3. **Batch Operations**: Add batch enqueue/dequeue operations
4. **Compression**: Add message compression support
5. **Metrics Integration**: Built-in Prometheus metrics
6. **Schema Evolution**: Support for message schema versioning