# Change: Replace Python logging with Loguru

## Why
The current standard Python logging implementation has limitations including verbose configuration, limited structured logging capabilities, and lacks modern features like automatic exception handling and better formatting options that Loguru provides out-of-the-box.

## What Changes
- Replace standard Python `logging` module with Loguru throughout the codebase
- Update logging configuration to use Loguru's simpler API
- Maintain all existing logging functionality while adding enhanced capabilities
- **BREAKING**: Changes to logging configuration API and environment variable names
- **BREAKING**: Potential changes to log output format

## Impact
- Affected specs: omniq-logging (new capability)
- Affected code: `src/omniq/logging.py`, all modules that import logging
- Dependencies: Add loguru as a required dependency
- Configuration: Update environment variables and configuration methods