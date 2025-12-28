# omniq-logging Specification

## Purpose
Provides Loguru-based logging system for OmniQ with enhanced features including structured logging, task correlation, and production-ready capabilities.
## Requirements
### Requirement: Basic Logging Configuration
The system SHALL provide simple logging configuration using standard Python logging with level control via environment variables.

#### Scenario: Configure log level
- **WHEN** developer sets OMNIQ_LOG_LEVEL environment variable
- **THEN** logging level is set accordingly

#### Scenario: Default logging
- **WHEN** no OMNIQ_LOG_LEVEL is set
- **THEN** default to INFO level

### Requirement: Loguru-based Logging System
OmniQ SHALL use Loguru as its primary logging system to provide enhanced logging capabilities with better configuration, structured logging, and exception handling.

#### Scenario: Basic logging configuration
- **WHEN** OmniQ initializes without explicit logging configuration
- **THEN** it SHALL use Loguru with default INFO level and standard formatting
- **AND** SHALL respect OMNIQ_LOG_LEVEL environment variable if set

#### Scenario: Structured logging
- **WHEN** logging task events or errors
- **THEN** the system SHALL support structured logging with contextual data
- **AND** SHALL include task_id, operation, and other relevant metadata in log entries

#### Scenario: Exception handling
- **WHEN** an exception occurs during task execution or storage operations
- **THEN** Loguru SHALL automatically capture and format exception details
- **AND** SHALL include full traceback information in error logs

### Requirement: Core Logging Functions
The system SHALL provide enhanced logging functions using Loguru while maintaining simple API surface.

**Change**: Enhanced from basic Python logging to Loguru-based implementation with additional features.

#### Scenario: Simplified API usage
- **WHEN** developer calls get_logger()
- **THEN** returns configured Loguru logger with smart defaults

### Requirement: Backward Compatibility Layer
OmniQ SHALL provide a backward compatibility layer to support existing code that uses the current logging API.

#### Scenario: Existing logging function calls
- **WHEN** existing code calls functions like `log_task_enqueued()` or `log_task_failed()`
- **THEN** these functions SHALL continue to work without modification
- **AND** SHALL delegate to Loguru internally

#### Scenario: Configuration migration
- **WHEN** users upgrade from standard logging to Loguru
- **THEN** the system SHALL provide clear migration documentation
- **AND** SHALL support both old and new configuration methods during transition

### Requirement: Enhanced Logging Configuration
OmniQ SHALL provide enhanced logging configuration options using Loguru's capabilities.

#### Scenario: Custom formatting
- **WHEN** users want custom log formatting
- **THEN** they SHALL be able to configure Loguru format strings
- **AND** SHALL support colorization, time formatting, and field customization

#### Scenario: Multiple handlers
- **WHEN** applications need to log to multiple destinations
- **THEN** the system SHALL support configuring multiple Loguru handlers
- **AND** SHALL allow different formats and levels per handler

#### Scenario: Log rotation and retention
- **WHEN** logging to files in production environments
- **THEN** the system SHALL support log rotation and retention policies
- **AND** SHALL allow configuration of file size limits and retention periods

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

