# Change: Simplify TaskError model and harden serialization contract

## Why
TaskError has scope drift (6 fields in proposal narrative, 14 in implementation), and JSONSerializer is tightly coupled to model internals with debug prints and brittle object hooks. This makes error handling fragile and increases cognitive load.

## What Changes
- **DECISION**: Reduce TaskError to 6-core-field minimal model for v1
  - error_type, message, timestamp, traceback, retry_count, is_retryable
  - Remove: severity, category, exception_type, context, max_retries
- Remove debug prints from JSONSerializer
- Remove model-aware coercion from serializer (tight coupling)
- Define stable wire format for TaskError (document in spec)
- Decide on JSON serializer v1 support (first-class vs deprecated)

## Impact
- **Affected specs**: omniq-api-config, task-storage-core
- **Affected code**: models.py, serialization.py, storage/*.py
- **Breaking**: Possible if reducing TaskError fields (backward compatible with defaults)
- **Risk**: Medium (touches serialization layer); mitigated by clear wire format spec

