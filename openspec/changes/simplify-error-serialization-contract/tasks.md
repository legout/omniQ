## 1. Spec
- [x] Define TaskError minimal 6-field model in proposal.md
- [x] Update spec deltas to show only 6 core fields
- [ ] Update `add-missing-task-models` proposal to align with 6-field decision
- [ ] Document wire format in specs
- [ ] Decide on JSON serializer v1 support (first-class vs deprecated)

## 2. Implementation
- [ ] Reduce TaskError from 14 to 6 fields
  - Remove: severity, category, exception_type, context, max_retries
  - Keep: error_type, message, timestamp, traceback, retry_count, is_retryable
- [ ] Update all storage backends to expect 6-field TaskError
- [ ] Update serialization to handle 6-field TaskError
- [ ] Remove debug prints from JSONSerializer
  - serialization.py:215-220 (already done in Phase 1)
- [ ] Remove model-specific code from JSONSerializer
  - Remove TaskError field mapping and auto-categorization
- [ ] Add backward compatibility handling for old 14-field data
- [ ] If deprecating JSON serializer:
    - Add deprecation warning in Settings
    - Update documentation
  - Otherwise:
    - Keep JSON as first-class option with simplified implementation

## 3. Tests
- [ ] Add tests for 6-field TaskError model
- [ ] Add serializer contract tests for stable wire format
- [ ] Add backward compatibility tests for old TaskError data
- [ ] Add privacy/security tests (verify no sensitive data in tracebacks)
