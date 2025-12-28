# Changelog

All notable changes to OmniQ will be documented in this file.

## [Unreleased]

### Added
- **TaskError Model**: Comprehensive structured error handling with error categorization, retry logic, and debugging context
- **Task Model Enhancement**: Added optional `error` field for structured error storage
- **Enhanced Error Handling**: Worker and core components now use TaskError for consistent error management
- **Storage Serialization**: All storage backends support TaskError serialization/deserialization
- **Helper Functions**: Added `has_error()`, `is_failed()`, and `get_error_message()` for convenient error checking
- **Backward Compatibility**: Existing tasks without errors continue to work (error field defaults to None)

### Changed
- **Queue Logic**: Fixed `max_retries` parameter handling to properly handle 0 values
- **Storage Schema**: Updated SQLite column mapping for correct field order
- **Error Handling**: Improved retry logic with proper TaskError integration

### Fixed
- **SQLite Storage**: Fixed column order mismatch in task retrieval and enqueue operations
- **Queue Logic**: Fixed max_retries parameter evaluation for non-zero values
- **TaskError Serialization**: Corrected error field mapping in storage backends

## [0.1.0] - 2025-12-01

### Added
- TaskError model with comprehensive error information
- Enhanced error handling throughout the codebase
- Structured error serialization and storage
- Backward compatibility for existing tasks

### Changed
- Improved retry logic and error categorization
- Enhanced storage backend error handling
- Updated queue parameter handling

### Fixed
- SQLite storage column mapping issues
- Queue max_retries parameter handling
- TaskError serialization bugs