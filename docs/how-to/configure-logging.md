# Configure Logging in DEV and PROD

Learn how to configure OmniQ's enhanced logging for development and production environments.

## Overview

OmniQ uses Loguru for enhanced logging with correlation IDs, structured output, and environment-based configuration. Use environment variables to switch between DEV and PROD modes.

## Logging Configuration

### Basic Configuration

```python
from omniq.logging import configure

# Simple configuration
configure(level="INFO")
```

### Environment-Based Configuration

```python
import os
from omniq.logging import configure

# Set mode via environment
os.environ["OMNIQ_LOG_MODE"] = "DEV"  # or "PROD"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"

# Configure reads from environment
configure()
```

## DEV Mode (Development)

DEV mode provides human-readable, colored console output for interactive development.

### Enable DEV Mode

```python
import os

os.environ["OMNIQ_LOG_MODE"] = "DEV"
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"

from omniq.logging import configure
configure()
```

### DEV Mode Features

- **Colored output**: Different colors for log levels
- **Detailed format**: Human-readable timestamps
- **Console only**: No file output
- **Full traces**: Complete exception tracebacks

### DEV Mode Output Example

```
2025-12-01 10:30:45 | INFO     | omniq.core:123 | Task execution started
└── task_id: abc-123 | operation: process_task | worker: worker-1
```

## PROD Mode (Production)

PROD mode provides machine-parseable JSON output for log aggregation and analysis.

### Enable PROD Mode

```python
import os

os.environ["OMNIQ_LOG_MODE"] = "PROD"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
os.environ["OMNIQ_LOG_FILE"] = "/var/log/omniq/app.log"
os.environ["OMNIQ_LOG_ROTATION"] = "100 MB"
os.environ["OMNIQ_LOG_RETENTION"] = "30 days"

from omniq.logging import configure
configure()
```

### PROD Mode Features

- **JSON output**: Structured, machine-parseable
- **File logging**: Persistent log storage
- **Automatic rotation**: Prevents disk space issues
- **Compression**: Rotated logs are compressed
- **Clean formatting**: Minimal, parseable format

### PROD Mode Output Example

```json
{
  "timestamp": "2025-12-01T10:30:45.123Z",
  "level": "INFO",
  "logger": "omniq.core",
  "message": "Task execution started",
  "task_id": "abc-123",
  "operation": "process_task",
  "worker": "worker-1"
}
```

## Log Levels

Configure logging verbosity:

```python
import os

# Development: see everything
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"

# Production: normal operations
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"

# Production with noise reduction
os.environ["OMNIQ_LOG_LEVEL"] = "WARNING"
```

### Log Level Hierarchy

```
DEBUG < INFO < WARNING < ERROR < CRITICAL
```

Setting a level logs that level and above:
- `DEBUG`: All messages
- `INFO`: INFO, WARNING, ERROR, CRITICAL
- `WARNING`: WARNING, ERROR, CRITICAL
- `ERROR`: ERROR, CRITICAL
- `CRITICAL`: CRITICAL only

## File Logging Configuration

Configure file output (PROD mode):

### File Path

```python
os.environ["OMNIQ_LOG_FILE"] = "/var/log/omniq/app.log"
# Default: logs/omniq.log
```

### Log Rotation

```python
os.environ["OMNIQ_LOG_ROTATION"] = "100 MB"
# Rotates when log file reaches 100 MB

# Can also use time-based rotation
os.environ["OMNIQ_LOG_ROTATION"] = "1 day"
# Rotates daily

# Or size + time
os.environ["OMNIQ_LOG_ROTATION"] = "100 MB 1 day"
```

### Log Retention

```python
os.environ["OMNIQ_LOG_RETENTION"] = "30 days"
# Keeps logs for 30 days

# Also supports time units
os.environ["OMNIQ_LOG_RETENTION"] = "1 week"
os.environ["OMNIQ_LOG_RETENTION"] = "1 month"
```

## Task Correlation

Bind task context to log messages for traceability:

### Using bind_task()

```python
from omniq.logging import bind_task

# Create logger with task context
logger = bind_task(
    task_id="task-123",
    operation="enqueue",
    worker="worker-1",
    custom_field="custom-value"
)

# All logs include correlation context
logger.info("Task enqueued")
```

Output (DEV mode):
```
2025-12-01 10:30:45 | INFO | ... | Task enqueued
└── task_id: task-123 | operation: enqueue | worker: worker-1 | custom_field: custom-value
```

### Using task_context()

```python
from omniq.logging import task_context

async def process_with_logging(task_id: str, data: str):
    with task_context(task_id, "process") as logger:
        logger.info(f"Processing: {data}")

        # Simulate work
        await asyncio.sleep(0.1)

        logger.info("Processing complete")
        return {"status": "success"}
```

The context manager automatically:
- Adds `task_id` to all logs
- Tracks execution timing
- Logs errors with proper context

## Environment Variables Reference

All logging environment variables:

| Variable | Description | Default | DEV/PROD |
|-----------|-------------|-----------|--------------|
| `OMNIQ_LOG_MODE` | Environment mode | `DEV` | Both |
| `OMNIQ_LOG_LEVEL` | Log level | `INFO` | Both |
| `OMNIQ_LOG_FILE` | Log file path (PROD) | `logs/omniq.log` | PROD |
| `OMNIQ_LOG_ROTATION` | Rotation size/time | `100 MB` | PROD |
| `OMNIQ_LOG_RETENTION` | Retention period | `30 days` | PROD |

## Complete Examples

### Development Configuration

```python
import os
from omniq.logging import configure

# DEV mode configuration
os.environ["OMNIQ_LOG_MODE"] = "DEV"
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"

configure()

# Get logger
logger = get_logger()
logger.debug("Debug information")
logger.info("Application started")
logger.warning("Warning message")
logger.error("Something went wrong")
```

### Production Configuration

```python
import os
from omniq.logging import configure

# PROD mode configuration
os.environ["OMNIQ_LOG_MODE"] = "PROD"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
os.environ["OMNIQ_LOG_FILE"] = "/var/log/omniq/app.log"
os.environ["OMNIQ_LOG_ROTATION"] = "100 MB"
os.environ["OMNIQ_LOG_RETENTION"] = "30 days"

configure()

# Get logger
logger = get_logger()
logger.info("Application started")

# With task correlation
from omniq.logging import bind_task

logger = bind_task("main", operation="startup")
logger.info("Task queue initialized")
```

### Docker Configuration

```dockerfile
FROM python:3.13

# Install OmniQ
COPY . /app
RUN pip install -e /app

# Set logging environment (PROD mode)
ENV OMNIQ_LOG_MODE=PROD
ENV OMNIQ_LOG_LEVEL=INFO
ENV OMNIQ_LOG_FILE=/var/log/omniq/app.log
ENV OMNIQ_LOG_ROTATION="100 MB"
ENV OMNIQ_LOG_RETENTION="30 days"

# Create log directory
RUN mkdir -p /var/log/omniq

# Mount log volume
VOLUME /var/log/omniq
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  omniq:
    build: .
    environment:
      OMNIQ_LOG_MODE: PROD
      OMNIQ_LOG_LEVEL: INFO
      OMNIQ_LOG_FILE: /var/log/omniq/app.log
      OMNIQ_LOG_ROTATION: "100 MB"
      OMNIQ_LOG_RETENTION: "30 days"
    volumes:
      - ./logs:/var/log/omniq
```

## Best Practices

### 1. Use DEV for Local Development

```python
# Local development: detailed logging
os.environ["OMNIQ_LOG_MODE"] = "DEV"
os.environ["OMNIQ_LOG_LEVEL"] = "DEBUG"
```

### 2. Use PROD for Production

```python
# Production: structured logging
os.environ["OMNIQ_LOG_MODE"] = "PROD"
os.environ["OMNIQ_LOG_LEVEL"] = "INFO"
```

### 3. Correlate All Logs

```python
# Bad: no correlation
logger.info("Task started")

# Good: with correlation
logger = bind_task(task_id="task-123", operation="execute")
logger.info("Task started")
```

### 4. Monitor Log Volumes

```bash
# Check disk space for logs
df -h /var/log/omniq

# Monitor log rotation
ls -lh /var/log/omniq/*.log.*
```

### 5. Use Log Aggregation

```python
# PROD JSON logs work with aggregation tools
# Supported: ELK Stack, Splunk, CloudWatch, etc.

# Example: Send to CloudWatch
import boto3

logs_client = boto3.client('logs')
logs_client.create_log_stream(logGroupName='omniq', logStreamName='production')
```

## Next Steps

- Learn [logging API reference](../reference/api/logging.md) for all functions
- Read [tutorial on logging](../tutorials/logging.md) for examples
- Understand [worker configuration](run-workers.md) with logging

## Summary

- **DEV mode**: Colored, human-readable console output (good for local dev)
- **PROD mode**: JSON file output with rotation (good for production)
- **Log levels**: Control verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Correlation**: Use `bind_task()` and `task_context()` for traceability
- **Configuration**: Environment variables provide flexible setup
- **Best practice**: DEV for development, PROD for production

Configure logging appropriately for your environment, use task correlation for traceability, and leverage JSON output for log aggregation in production.
