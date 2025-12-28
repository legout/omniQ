## 1. Spec
- [x] Define TaskError minimal 6-field model in proposal.md
- [x] Update spec deltas to show only 6 core fields
- [x] Update `add-missing-task-models` proposal to align with 6-field decision
- [x] Document wire format in specs
- [x] Decide on JSON serializer v1 support (first-class vs deprecated)

## 2. Implementation
- [x] Reduce TaskError from 11 to 6 fields
  - Remove: severity, category, exception_type, context, max_retries
  - Keep: error_type, message, timestamp, traceback, retry_count, is_retryable
- [x] Update all storage backends to expect 6-field TaskError
- [x] Update serialization to handle 6-field TaskError
- [x] Remove debug prints from JSONSerializer
  - serialization.py:215-220 (already done in Phase 1)
- [x] Remove model-specific code from JSONSerializer
  - Remove TaskError field mapping and auto-categorization
- [x] Add backward compatibility handling for old TaskError data
- [x] If deprecating JSON serializer:
    - Add deprecation warning in Settings
    - Update documentation
  - Otherwise:
    - Keep JSON as first-class option with simplified implementation

## 3. Tests
- [x] Add tests for 6-field TaskError model
- [x] Add serializer contract tests for stable wire format
- [x] Add backward compatibility tests for old TaskError data
- N/A Add privacy/security tests (verify no sensitive data in tracebacks) - deferred per user decision
