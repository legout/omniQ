## 1. Public API
- [x] 1.1 Implement `AsyncOmniQ` and `OmniQ` in `src/omniq/core.py` with methods for `enqueue`, `get_result`, and `worker`.
- [x] 1.2 Ensure `OmniQ` provides blocking wrappers around the async methods using a centralized async runner.
- [x] 1.3 Add minimal public re-exports in `src/omniq/__init__.py` for façade types and key models.

## 2. Settings and Environment
- [x] 2.1 Define a `Settings` type in `src/omniq/config.py` with fields for backend, database URL, base directory, default timeout, default max retries, result TTL, and serializer.
- [x] 2.2 Implement `from_env()` to construct `Settings` from environment variables (`OMNIQ_BACKEND`, `OMNIQ_DB_URL`, `OMNIQ_BASE_DIR`, `OMNIQ_DEFAULT_TIMEOUT`, `OMNIQ_DEFAULT_MAX_RETRIES`, `OMNIQ_RESULT_TTL`, `OMNIQ_SERIALIZER`, `OMNIQ_LOG_LEVEL`).
- [x] 2.3 Document defaults and validation behavior for invalid or missing env values.

## 3. Serialization and Logging
- [x] 3.1 Implement a `Serializer` protocol and concrete `MsgspecSerializer` / `CloudpickleSerializer` in `src/omniq/serialization.py`.
- [x] 3.2 Wire serializer selection into settings so msgspec is the default and cloudpickle is an explicit opt-in.
- [x] 3.3 Configure library logging to use the standard Python logging system and honor `OMNIQ_LOG_LEVEL`.

