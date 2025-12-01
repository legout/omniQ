# Change: Simplify logging to meet v1 compliance requirements

## Why
Current logging implementation is 300+ lines with Loguru, structured logging, fallback mechanisms - far beyond v1's requirement for "Standard Python logging for library internals". This violates v1's goal of being "small enough to understand in less than a day" and adds unnecessary complexity.

## What Changes
- Replace Loguru with standard Python `logging` module (~50 lines total)
- Remove structured logging, fallback mechanisms, file rotation features
- Keep only basic level control via `OMNIQ_LOG_LEVEL` environment variable
- Remove advanced logging features and extra environment variables
- **BREAKING**: Remove Loguru dependency and advanced logging features
- **BREAKING**: Simplify logging configuration API

## Impact
- Affected specs: omniq-logging (complete rewrite)
- Affected code: `src/omniq/logging.py`, `src/omniq/core.py`
- Dependencies: Remove loguru dependency from pyproject.toml
- Configuration: Simplify to basic level control only