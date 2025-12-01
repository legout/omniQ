## ADDED Requirements

### Requirement: Enhanced Logging API with Loguru
The system SHALL provide enhanced logging using Loguru with simplified configuration while maintaining v1 compliance.

#### Scenario: Basic logging setup
- **WHEN** developer calls configure() with no parameters
- **THEN** logging is configured with smart defaults for current environment

#### Scenario: Task execution with correlation
- **WHEN** developer uses task_context() with task_id and operation
- **THEN** all logs within context include correlation ID and timing

### Requirement: Production-Ready Log Features
The system SHALL provide essential production logging features including rotation, compression, and structured output.

#### Scenario: Production logging configuration
- **WHEN** system runs in PROD mode (OMNIQ_LOG_MODE=PROD)
- **THEN** logs output in JSON format with automatic rotation

#### Scenario: Environment-based configuration
- **WHEN** OMNIQ_LOG_LEVEL environment variable is set
- **THEN** logging level is configured accordingly

### Requirement: Task Observability
The system SHALL provide correlation IDs and execution tracing for task operations.

#### Scenario: Task execution tracing
- **WHEN** task_context() is used with task_id
- **THEN** log entries include correlation_id, operation, and timing

### Requirement: Performance and Reliability
The system SHALL provide non-blocking async logging with graceful fallback.

#### Scenario: High-volume logging
- **WHEN** logging 10,000 messages
- **THEN** operation completes in under 1 second

#### Scenario: Concurrent logging
- **WHEN** multiple threads log simultaneously
- **THEN** all messages are captured without corruption

## MODIFIED Requirements

### Requirement: Core Logging Functions
The system SHALL provide enhanced logging functions using Loguru while maintaining simple API surface.

**Change**: Enhanced from basic Python logging to Loguru-based implementation with additional features.

#### Scenario: Simplified API usage
- **WHEN** developer calls get_logger()
- **THEN** returns configured Loguru logger with smart defaults

## REMOVED Requirements

### Requirement: Simplified Logging Only
**Reason**: Restores essential production features while maintaining v1 compliance
**Migration**: Enhanced Loguru implementation provides drop-in replacement

## Design

### API Surface

```python
def configure(
    level: str = "INFO",
    format: str | None = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "gz"
) -> None:
    """Configure OmniQ logging with smart defaults."""

def get_logger(name: str = "omniq") -> Logger:
    """Get configured logger instance."""

def task_context(task_id: str, operation: str) -> ContextManager:
    """Context manager for task execution logging."""

def bind_task(task_id: str, **kwargs) -> Logger:
    """Bind correlation ID and additional context to logger."""
```

### Configuration

#### Environment Variables
- `OMNIQ_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `OMNIQ_LOG_MODE`: Environment mode (DEV, PROD)
- `OMNIQ_LOG_FILE`: Log file path (default: logs/omniq.log)
- `OMNIQ_LOG_ROTATION`: Log rotation size (default: 100 MB)
- `OMNIQ_LOG_RETENTION`: Log retention period (default: 30 days)

#### Smart Defaults
- **DEV mode**: Console output with colors, detailed formatting
- **PROD mode**: File output with JSON format, rotation enabled

### Log Format

#### DEV Format
```
2025-12-01 10:30:45 | INFO     | omniq.core:123 | Task execution started
└── task_id: abc-123 | operation: process_task | worker: worker-1
```

#### PROD Format (JSON)
```json
{
  "timestamp": "2025-12-01T10:30:45.123Z",
  "level": "INFO",
  "logger": "omniq.core",
  "message": "Task execution started",
  "task_id": "abc-123",
  "operation": "process_task",
  "worker": "worker-1",
  "correlation_id": "abc-123"
}
```

## Implementation Details

### File Structure
- `src/omniq/logging.py`: Main implementation (~80 lines)
- Configuration and formatters
- Task context managers
- Environment-based setup

### Dependencies
- `loguru`: Enhanced logging library
- Standard library: `os`, `sys`, `contextlib`, `typing`

### Error Handling
- Graceful fallback if log directory unavailable
- No exceptions raised from logging failures
- Warning messages for configuration issues

## Testing Strategy

### Unit Tests
- API function behavior
- Environment variable handling
- Task context and correlation IDs
- Log rotation and formatting

### Integration Tests
- Task execution with logging
- Multi-worker scenarios
- Performance impact measurement
- Production deployment scenarios

## Migration Path

### From Simplified Logging
- Drop-in replacement for existing API
- Enhanced features available automatically
- Configuration via environment variables
- No breaking changes to existing code

### Configuration Examples
```python
# Basic usage (works with defaults)
from omniq.logging import get_logger, task_context

logger = get_logger()
with task_context("task-123", "process"):
    logger.info("Processing task")

# Advanced usage
from omniq.logging import configure, bind_task

configure(level="DEBUG", rotation="50 MB")
logger = bind_task("task-123", worker="worker-1")
logger.info("Task processing started")
```

## Success Criteria

1. All existing tests pass without modification
2. Log rotation works in production scenarios
3. Task correlation IDs propagate correctly
4. Performance impact is <5% on task execution
5. Configuration works via environment variables
6. API surface remains at 4 functions maximum
7. Documentation is clear and examples work

## Design

### API Surface

```python
def configure(
    level: str = "INFO",
    format: str | None = None,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "gz"
) -> None:
    """Configure OmniQ logging with smart defaults."""

def get_logger(name: str = "omniq") -> Logger:
    """Get configured logger instance."""

def task_context(task_id: str, operation: str) -> ContextManager:
    """Context manager for task execution logging."""

def bind_task(task_id: str, **kwargs) -> Logger:
    """Bind correlation ID and additional context to logger."""
```

### Configuration

#### Environment Variables
- `OMNIQ_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `OMNIQ_LOG_MODE`: Environment mode (DEV, PROD)
- `OMNIQ_LOG_FILE`: Log file path (default: logs/omniq.log)
- `OMNIQ_LOG_ROTATION`: Log rotation size (default: 100 MB)
- `OMNIQ_LOG_RETENTION`: Log retention period (default: 30 days)

#### Smart Defaults
- **DEV mode**: Console output with colors, detailed formatting
- **PROD mode**: File output with JSON format, rotation enabled

### Log Format

#### DEV Format
```
2025-12-01 10:30:45 | INFO     | omniq.core:123 | Task execution started
└── task_id: abc-123 | operation: process_task | worker: worker-1
```

#### PROD Format (JSON)
```json
{
  "timestamp": "2025-12-01T10:30:45.123Z",
  "level": "INFO",
  "logger": "omniq.core",
  "message": "Task execution started",
  "task_id": "abc-123",
  "operation": "process_task",
  "worker": "worker-1",
  "correlation_id": "abc-123"
}
```

## Implementation Details

### File Structure
- `src/omniq/logging.py`: Main implementation (~80 lines)
- Configuration and formatters
- Task context managers
- Environment-based setup

### Dependencies
- `loguru`: Enhanced logging library
- Standard library: `os`, `sys`, `contextlib`, `typing`

### Error Handling
- Graceful fallback if log directory unavailable
- No exceptions raised from logging failures
- Warning messages for configuration issues

## Testing Strategy

### Unit Tests
- API function behavior
- Environment variable handling
- Task context and correlation IDs
- Log rotation and formatting

### Integration Tests
- Task execution with logging
- Multi-worker scenarios
- Performance impact measurement
- Production deployment scenarios

## Migration Path

### From Simplified Logging
- Drop-in replacement for existing API
- Enhanced features available automatically
- Configuration via environment variables
- No breaking changes to existing code

### Configuration Examples
```python
# Basic usage (works with defaults)
from omniq.logging import get_logger, task_context

logger = get_logger()
with task_context("task-123", "process"):
    logger.info("Processing task")

# Advanced usage
from omniq.logging import configure, bind_task

configure(level="DEBUG", rotation="50 MB")
logger = bind_task("task-123", worker="worker-1")
logger.info("Task processing started")
```

## Success Criteria

1. All existing tests pass without modification
2. Log rotation works in production scenarios
3. Task correlation IDs propagate correctly
4. Performance impact is <5% on task execution
5. Configuration works via environment variables
6. API surface remains at 4 functions maximum
7. Documentation is clear and examples work