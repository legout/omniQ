# OpenSpec: TaskError Model Specification

## Overview

This specification defines the `TaskError` model that provides structured error information for failed tasks in the OmniQ system.

## ADDED Requirements

### Requirement: TaskError Model
The system SHALL provide a comprehensive TaskError model for structured error information. The TaskError MUST support exception creation, serialization, and retry logic.

#### Scenario: TaskError Creation from Exception
```python
# When a worker encounters an exception during task execution
try:
    result = await task_func(*task.args, **task.kwargs)
except Exception as e:
    # Should create a TaskError with exception details
    error = TaskError.from_exception(
        exception=e,
        error_type="runtime",
        is_retryable=True
    )
    task.error = error
    task.status = TaskStatus.FAILED
```

#### Scenario: TaskError Serialization
```python
# When storing a task with error to file storage
task_with_error = Task(
    id="task-123",
    status=TaskStatus.FAILED,
    error=TaskError(
        error_type="timeout",
        message="Task exceeded 30 second timeout",
        timestamp=datetime.utcnow(),
        is_retryable=True
    )
)
# Should serialize and deserialize without data loss
serialized = task_with_error.to_dict()
deserialized = Task.from_dict(serialized)
assert deserialized.error.error_type == "timeout"
```

### Requirement: Performance and Memory Requirements
The TaskError model MUST meet performance requirements with creation time under 1ms and MUST have minimal memory overhead. The system SHALL ensure efficient serialization and deserialization.

#### Scenario: Performance Requirements
```python
# TaskError creation should be fast (<1ms)
import time
start = time.perf_counter()
error = TaskError.from_exception(ValueError("test error"))
duration = time.perf_counter() - start
assert duration < 0.001  # Less than 1ms
```

## MODIFIED Requirements

### Requirement: Task Model Enhancement
The Task model SHALL be modified to include optional error field. The system MUST provide convenience methods for error checking and MUST maintain backward compatibility.

#### Scenario: Task with Error Field
```python
# Task model should support optional error field
task = Task(
    id="task-123",
    status=TaskStatus.FAILED,
    error=TaskError(
        error_type="validation",
        message="Invalid input parameters",
        is_retryable=False
    )
)

# Should provide convenience methods
assert task.has_error() == True
assert task.is_failed() == True
assert task.get_error_message() == "Invalid input parameters"
```

## API Specification

### TaskError Model

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict
from enum import Enum

class ErrorType(Enum):
    """Standard error types for categorization."""
    RUNTIME = "runtime"           # Runtime errors during execution
    TIMEOUT = "timeout"           # Task timeout errors
    VALIDATION = "validation"     # Input validation errors
    RESOURCE = "resource"         # Resource exhaustion errors
    NETWORK = "network"           # Network-related errors
    SYSTEM = "system"             # System-level errors
    USER = "user"                 # User-defined errors
    UNKNOWN = "unknown"           # Unclassified errors

@dataclass
class TaskError:
    """Structured error information for failed tasks."""
    
    # Core error information
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Optional detailed information
    traceback: Optional[str] = None
    exception_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    # Retry information
    retry_count: int = 0
    is_retryable: bool = True
    max_retries: Optional[int] = None
    
    # Error classification
    severity: str = "error"  # "warning", "error", "critical"
    category: str = "unknown"
    
    def __post_init__(self) -> None:
        """Validate and normalize error data."""
        # Normalize error_type to lowercase
        self.error_type = self.error_type.lower()
        
        # Validate severity
        valid_severities = {"warning", "error", "critical"}
        if self.severity not in valid_severities:
            self.severity = "error"
        
        # Auto-categorize based on error_type if not set
        if self.category == "unknown":
            self.category = self._auto_categorize()
    
    def _auto_categorize(self) -> str:
        """Auto-categorize error based on error_type."""
        error_type_mapping = {
            "timeout": "system",
            "validation": "user",
            "resource": "system",
            "network": "external",
            "runtime": "application",
        }
        return error_type_mapping.get(self.error_type, "unknown")
    
    def can_retry(self) -> bool:
        """Check if error is retryable based on count and configuration."""
        if not self.is_retryable:
            return False
        
        if self.max_retries is not None:
            return self.retry_count < self.max_retries
        
        return True
    
    def increment_retry(self) -> "TaskError":
        """Create a new TaskError with incremented retry count."""
        return TaskError(
            error_type=self.error_type,
            message=self.message,
            timestamp=self.timestamp,
            traceback=self.traceback,
            exception_type=self.exception_type,
            context=self.context,
            retry_count=self.retry_count + 1,
            is_retryable=self.is_retryable,
            max_retries=self.max_retries,
            severity=self.severity,
            category=self.category,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
            "exception_type": self.exception_type,
            "context": self.context,
            "retry_count": self.retry_count,
            "is_retryable": self.is_retryable,
            "max_retries": self.max_retries,
            "severity": self.severity,
            "category": self.category,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskError":
        """Create TaskError from dictionary."""
        # Handle timestamp conversion
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            from datetime import datetime
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()
        
        return cls(
            error_type=data.get("error_type", "unknown"),
            message=data.get("message", ""),
            timestamp=timestamp,
            traceback=data.get("traceback"),
            exception_type=data.get("exception_type"),
            context=data.get("context"),
            retry_count=data.get("retry_count", 0),
            is_retryable=data.get("is_retryable", True),
            max_retries=data.get("max_retries"),
            severity=data.get("severity", "error"),
            category=data.get("category", "unknown"),
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        message: Optional[str] = None,
        error_type: str = "runtime",
        is_retryable: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> "TaskError":
        """Create TaskError from exception."""
        import traceback
        
        return cls(
            error_type=error_type,
            message=message or str(exception),
            traceback=traceback.format_exc(),
            exception_type=type(exception).__name__,
            context=context,
            is_retryable=is_retryable,
        )
```

### Task Model Updates

```python
@dataclass
class Task:
    # ... existing fields ...
    error: Optional[TaskError] = None
    
    def has_error(self) -> bool:
        """Check if task has an error."""
        return self.error is not None
    
    def is_failed(self) -> bool:
        """Check if task is in failed state."""
        return self.status == TaskStatus.FAILED or self.has_error()
    
    def get_error_message(self) -> Optional[str]:
        """Get error message if task has error."""
        return self.error.message if self.error else None
```

## Implementation Details

### Error Creation Patterns

```python
# From exception
error = TaskError.from_exception(
    exception=ValueError("Invalid input"),
    error_type="validation",
    is_retryable=False
)

# Manual creation
error = TaskError(
    error_type="timeout",
    message="Task exceeded 30 second timeout",
    is_retryable=True,
    max_retries=3
)

# With context
error = TaskError(
    error_type="resource",
    message="Memory limit exceeded",
    context={"memory_limit": "512MB", "usage": "600MB"},
    is_retryable=False
)
```

### Integration Points

1. **Worker Integration**: Create TaskError when exceptions occur
2. **Core Integration**: Handle TaskError in task results and status transitions
3. **Storage Integration**: Serialize/deserialize TaskError with tasks
4. **API Integration**: Expose error information in task results

### Backward Compatibility

- Existing tasks without `error` field get `None` (safe default)
- Storage backends handle missing error gracefully
- Serialization supports both old and new formats

## Testing Requirements

### Unit Tests

1. **TaskError Creation**: Test all creation methods and validation
2. **Serialization**: Test to_dict/from_dict roundtrip
3. **Retry Logic**: Test can_retry() and increment_retry()
4. **Auto-categorization**: Test error type to category mapping
5. **Exception Handling**: Test from_exception() method

### Integration Tests

1. **Worker Error Handling**: Test worker creates TaskError on exceptions
2. **Core Error Flow**: Test core handles TaskError in results
3. **Storage Serialization**: Test storage backends handle TaskError
4. **Backward Compatibility**: Test old tasks without errors work

### Performance Tests

1. **Error Creation Overhead**: Measure TaskError creation performance
2. **Memory Usage**: Test memory impact of TaskError objects
3. **Serialization Performance**: Test TaskError serialization speed

## Migration Guide

### For Existing Code

1. **Task Usage**: No changes required, error field defaults to None
2. **Error Handling**: Gradually migrate to use TaskError where appropriate
3. **Storage**: Existing serialized tasks continue to work

### For New Code

1. **Use TaskError.from_exception()** for exception handling
2. **Set appropriate error_type** for better categorization
3. **Configure retryability** based on error characteristics
4. **Add context** for better debugging

## Security Considerations

1. **Traceback Sanitization**: Consider sanitizing tracebacks for sensitive data
2. **Context Validation**: Validate context data doesn't contain secrets
3. **Error Message Filtering**: Avoid exposing sensitive information in messages

## Future Extensions

1. **Error Aggregation**: Support for error grouping and analysis
2. **Custom Error Types**: Allow user-defined error categories
3. **Error Recovery**: Support for automatic error recovery strategies
4. **Error Metrics**: Integration with monitoring and metrics systems