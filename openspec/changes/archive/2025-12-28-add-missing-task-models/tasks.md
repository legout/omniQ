# Implementation Tasks: Add Missing Task Models for v1 Compliance

## Overview

These tasks implement the missing `TaskError` model with 6 core fields and standardize error handling throughout the OmniQ codebase to achieve full v1 compliance. Note: TaskError uses 6 core fields (error_type, message, timestamp, traceback, retry_count, is_retryable) and does NOT include context parameter.

## Task Dependencies

```
Task 1 (Foundation) → Task 2 → Task 3 → Task 4 → Task 5 (Testing) → Task 6 (Documentation)
```

## Tasks

### Task 1: Add TaskError Model to models.py
**Priority**: HIGH  
**Estimated Time**: 30 minutes  
**Dependencies**: None

**Steps**:
1. Add TaskError dataclass to `src/omniq/models.py`
2. Include required fields: error_type, message, timestamp, traceback, retry_count, is_retryable
3. Add type hints following existing patterns
4. Add basic validation for required fields
5. Add __post_init__ method for timestamp defaults

**Acceptance Criteria**:
- [x] TaskError model implemented with all required fields
- [x] Type hints match existing codebase patterns
- [x] Basic validation in place
- [x] Model follows existing dataclass patterns

### Task 2: Update Task Model with Error Field
**Priority**: HIGH  
**Estimated Time**: 15 minutes  
**Dependencies**: Task 1

**Steps**:
1. Add `error: Optional[TaskError] = None` field to Task model
2. Update Task imports to include TaskError
3. Ensure backward compatibility with existing serialization
4. Update any Task constructors to handle error field

**Acceptance Criteria**:
- [x] Task model has error field with proper default
- [x] Backward compatibility maintained
- [x] No breaking changes to existing Task usage

### Task 3: Update Worker Error Handling
**Priority**: MEDIUM  
**Estimated Time**: 45 minutes  
**Dependencies**: Task 2

**Steps**:
1. Update `src/omniq/worker.py` to use TaskError for exception handling
2. Replace current error storage with TaskError objects
3. Update retry logic to use TaskError.retry_count
4. Add proper error categorization (retryable vs non-retryable)
5. Update logging to use TaskError information

**Acceptance Criteria**:
- [x] Worker creates TaskError objects on failures
- [x] Retry logic uses TaskError.retry_count
- [x] Error categorization implemented
- [x] Logging uses TaskError context

### Task 4: Update Core Error Handling
**Priority**: MEDIUM  
**Estimated Time**: 30 minutes  
**Dependencies**: Task 2

**Steps**:
1. Update `src/omniq/core.py` to handle TaskError in task results
2. Update task status transitions to consider error state
3. Add error propagation in task execution flow
4. Update any error validation logic

**Acceptance Criteria**:
- [x] Core properly handles TaskError in task results
- [x] Status transitions work with error states
- [x] Error propagation implemented correctly
- [x] No breaking changes to existing API

### Task 5: Update Storage Error Serialization
**Priority**: MEDIUM  
**Estimated Time**: 45 minutes  
**Dependencies**: Task 2

**Steps**:
1. Update `src/omniq/storage/file.py` to serialize/deserialize TaskError
2. Update `src/omniq/storage/sqlite.py` to handle TaskError field
3. Update `src/omniq/storage/base.py` if needed for error handling
4. Test error serialization roundtrip
5. Handle backward compatibility for old tasks without errors

**Acceptance Criteria**:
- [x] File storage properly serializes TaskError
- [x] SQLite storage handles TaskError field
- [x] Backward compatibility maintained
- [x] Error serialization roundtrip works

### Task 6: Add Comprehensive Tests
**Priority**: MEDIUM  
**Estimated Time**: 60 minutes  
**Dependencies**: Task 5

**Steps**:
1. Create tests for TaskError model creation and validation
2. Add tests for worker error handling with TaskError
3. Add tests for core error handling
4. Add storage serialization tests for TaskError
5. Add backward compatibility tests
6. Add integration tests for end-to-end error flow

**Acceptance Criteria**:
- [x] TaskError model fully tested
- [x] Worker error handling tested
- [x] Core error handling tested
- [x] Storage serialization tested
- [x] Backward compatibility verified
- [x] Integration tests pass

### Task 7: Update Documentation
**Priority**: LOW  
**Estimated Time**: 30 minutes  
**Dependencies**: Task 6

**Steps**:
1. Update model documentation to include TaskError
2. Add error handling examples to API docs
3. Update migration guide with error field info
4. Add TaskError to changelog

**Acceptance Criteria**:
- [x] Documentation updated for TaskError
- [x] Examples provided for error handling
- [x] Migration guide updated
- [x] Changelog updated

## Testing Strategy

### Unit Tests
- TaskError model validation
- Error handling in worker and core
- Storage serialization for TaskError

### Integration Tests
- End-to-end error flow from worker to storage
- Backward compatibility with existing tasks
- Error retry logic with TaskError

### Regression Tests
- Existing functionality unchanged
- Performance impact minimal
- Memory usage acceptable

## Rollback Plan

If issues arise:
1. Revert Task model changes (remove error field)
2. Remove TaskError model
3. Restore previous error handling in worker/core
4. Undo storage serialization changes
5. Undo queue parameter handling fix

## Success Metrics

- All tests passing
- Full v1 PRD compliance achieved
- No breaking changes for existing users
- Error handling improved and standardized