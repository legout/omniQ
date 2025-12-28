# OpenSpec: API Compliance Fixes

## Overview

This specification addresses critical API compliance issues to achieve full v1 compliance.

## MODIFIED Requirements

### Requirement: Configuration API Fixes
The configuration API SHALL be fixed to meet v1 compliance requirements. The system MUST use msgspec as default serializer and MUST support environment-based configuration.

#### Scenario: Default Serializer Compliance
```python
# Default configuration should use msgspec for security
config = OmniQConfig()
assert config.serializer == "msgspec"  # Not "json"

# Should be explicitly configurable
config = OmniQConfig(serializer="json")
assert config.serializer == "json"
```

#### Scenario: Environment Constructor
```python
# Should create OmniQ from environment variables
os.environ["OMNIQ_STORAGE_BACKEND"] = "sqlite"
os.environ["OMNIQ_STORAGE_DB_URL"] = "sqlite:///tasks.db"

omniq = OmniQ.from_env()
assert isinstance(omniq.storage, SQLiteStorage)
assert omniq.config.storage.db_url == "sqlite:///tasks.db"
```

### Requirement: Storage Backend Factory
The storage backend factory SHALL properly instantiate backends from configuration. The factory MUST support all configured backend types and MUST handle configuration errors gracefully.

#### Scenario: SQLite Backend Configuration
```python
# Should properly configure SQLite from config
config = OmniQConfig(
    storage=StorageConfig(
        backend="sqlite",
        db_url="sqlite:///custom.db"
    )
)
storage = create_storage(config.storage)
assert isinstance(storage, SQLiteStorage)
assert storage.db_path == "custom.db"
```

### Requirement: Task Model Enhancement
The Task model SHALL be enhanced with optional error field while maintaining backward compatibility. The system MUST ensure existing code continues to work without modification.

#### Scenario: Task Error Field
```python
# Task should support optional error field
task = Task(
    id="task-123",
    status=TaskStatus.FAILED,
    error=TaskError(
        error_type="runtime",
        message="Something went wrong"
    )
)

# Existing tasks without errors should work
old_task = Task(id="old-task", status=TaskStatus.PENDING)
assert old_task.error is None
```

## ADDED Requirements

### Requirement: Configuration Validation
The system SHALL provide comprehensive configuration validation with clear error messages. Configuration validation MUST catch invalid settings before runtime and MUST provide helpful error messages.

#### Scenario: Configuration Validation
```python
# Should validate SQLite configuration
with pytest.raises(ValueError, match="db_url is required"):
    config = OmniQConfig(storage=StorageConfig(backend="sqlite"))
    validate_config(config)  # Should raise error

# Should provide helpful error messages
with pytest.raises(ValueError, match="Invalid storage backend"):
    config = OmniQConfig(storage=StorageConfig(backend="invalid"))
    validate_config(config)
```

### Requirement: API Convenience Methods
The API SHALL provide convenient factory methods for common configuration patterns. These methods MUST simplify common use cases and MUST follow consistent naming conventions.

#### Scenario: Factory Methods
```python
# Should provide convenient factory methods
omniq = OmniQ.with_sqlite("sqlite:///tasks.db")
assert isinstance(omniq.storage, SQLiteStorage)

omniq = OmniQ.with_file_storage("/tmp/tasks")
assert isinstance(omniq.storage, FileStorage)
```