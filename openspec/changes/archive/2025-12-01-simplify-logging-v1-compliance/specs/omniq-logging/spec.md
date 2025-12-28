## MODIFIED Requirements
### Requirement: Basic Logging Configuration
The system SHALL provide simple logging configuration using standard Python logging with level control via environment variables.

#### Scenario: Configure log level
- **WHEN** developer sets OMNIQ_LOG_LEVEL environment variable
- **THEN** logging level is set accordingly

#### Scenario: Default logging
- **WHEN** no OMNIQ_LOG_LEVEL is set
- **THEN** default to INFO level

## REMOVED Requirements
### Requirement: Structured Logging
**Reason**: Beyond v1 scope - adds unnecessary complexity
**Migration**: Use standard Python logging format strings

### Requirement: Loguru Integration
**Reason**: Beyond v1 requirements - violates "small enough to understand in less than a day"
**Migration**: Replace with standard Python logging module

### Requirement: Fallback Logging
**Reason**: Over-engineering for v1 - adds unnecessary complexity
**Migration**: Use single logging implementation

### Requirement: File Rotation and Compression
**Reason**: Advanced feature beyond v1 scope
**Migration**: Remove rotation and compression capabilities

### Requirement: Multiple Environment Variables
**Reason**: Over-complex for v1 - confuses users
**Migration**: Use only OMNIQ_LOG_LEVEL