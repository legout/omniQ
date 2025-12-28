# OpenSpec Change Proposal: Add Missing Task Models for v1 Compliance

## Why
The current implementation is missing critical components required by the v1 PRD: the TaskError model is not implemented, error handling is inconsistent, and different parts of the codebase use different error approaches. This prevents full v1 compliance and makes error tracking difficult.

## Summary

This proposal adds the missing `TaskError` model and updates error handling throughout the codebase to achieve full v1 compliance with the PRD requirements.

## What Changes
- Add TaskError model to `src/omniq/models.py` with comprehensive error information
- Update Task model to include optional error field
- Modify worker error handling to use TaskError consistently
- Update core error handling to work with TaskError
- Update storage backends to serialize/deserialize TaskError
- Add comprehensive tests for TaskError functionality
- **BREAKING**: Task model gains new error field (backward compatible with default None)

## Problem Statement

The current implementation is missing critical components required by the v1 PRD:

1. **Missing TaskError Model**: The PRD specifies a `TaskError` model but it's not implemented
2. **Incomplete Error Handling**: Error states and transitions are not properly modeled
3. **Inconsistent Error Types**: Different parts of the codebase use different error approaches

## Proposed Solution

### 1. Add TaskError Model

Create a comprehensive `TaskError` model following the existing pattern:

```python
@dataclass
class TaskError:
    """Error information for failed tasks."""
    error_type: str
    message: str
    timestamp: datetime
    traceback: Optional[str] = None
    retry_count: int = 0
    is_retryable: bool = True
```

### 2. Update Task Model

Add error field to Task model:

```python
@dataclass
class Task:
    # ... existing fields ...
    error: Optional[TaskError] = None
```

### 3. Standardize Error Handling

Create consistent error handling patterns across all components.

## Impact Analysis

### Benefits
- **PRD Compliance**: Adds missing TaskError model required by v1 spec
- **Consistency**: Standardizes error handling across the codebase
- **Reliability**: Improves error tracking and debugging capabilities
- **Simplicity**: Uses existing patterns and conventions

### Risks
- **Breaking Changes**: Task model gains a new field (backward compatible with default)
- **Migration**: Existing tasks without errors will get None (safe default)

## Alternatives Considered

1. **Use Exception Classes Only**: Insufficient for persistent error storage
2. **String Error Messages**: Lacks structured error information
3. **Complex Error Hierarchy**: Over-engineering for v1 requirements

## Implementation Plan

See `tasks.md` for detailed implementation steps.

## Success Criteria

- [ ] TaskError model implemented and tested
- [ ] Task model updated with error field
- [ ] All error handling uses TaskError consistently
- [ ] Backward compatibility maintained
- [ ] Full v1 PRD compliance achieved

## Files to Change

### New Files
- `src/omniq/models.py` - Add TaskError model, update Task model

### Modified Files
- `src/omniq/worker.py` - Update error handling to use TaskError
- `src/omniq/core.py` - Update error handling to use TaskError
- `src/omniq/storage/*.py` - Update error serialization

## Testing Strategy

- Unit tests for TaskError model creation and validation
- Integration tests for error handling in worker and core
- Backward compatibility tests for existing task serialization
- Error scenario tests for retry logic

## Documentation Updates

- Update model documentation to include TaskError
- Add error handling examples to API documentation
- Update migration guide with error field information

## OpenSpec Validation

```bash
openspec validate --strict
```

## Approval

- [ ] Technical review completed
- [ ] API compliance verified
- [ ] Backward compatibility confirmed
- [ ] Tests passing
- [ ] Documentation updated

---

**Change ID**: `add-missing-task-models`  
**Date**: 2025-12-01  
**Priority**: HIGH (PRD compliance)  
**Breaking Change**: No (backward compatible)