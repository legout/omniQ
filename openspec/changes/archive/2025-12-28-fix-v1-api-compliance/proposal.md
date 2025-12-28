# OpenSpec Change Proposal: Fix v1 API Compliance Issues

## Why
Multiple API compliance issues including wrong default serializer ("json" vs "msgspec"), missing `OmniQ.from_env()` constructor, incomplete storage backend factory, and missing `TaskError` model. These issues prevent v1 compliance and could cause runtime errors.

## What Changes
- Fix default serializer to "msgspec" for security compliance
- Add `OmniQ.from_env()` convenience constructor
- Fix SQLite backend to properly use `db_url` setting
- Add missing `TaskError` model to `models.py`
- Update configuration validation for SQLite requirements
- **BREAKING**: Default serializer change affects task serialization
- **BREAKING**: Configuration validation changes

## Impact
- Affected specs: omniq-api-config (modify), task-storage-core (modify)
- Affected code: `src/omniq/config.py`, `src/omniq/core.py`, `src/omniq/models.py`, `src/omniq/storage/sqlite.py`
- API: Improve compliance with v1 specification requirements