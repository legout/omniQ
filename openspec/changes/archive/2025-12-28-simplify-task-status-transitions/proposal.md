# OpenSpec Change Proposal: Simplify Task Status Transitions for v1 Compliance

## Why
The current implementation has over-engineered task status validation that violates v1 goals: excessive complexity with 300+ lines of validation code, performance impact from complex validation on every status transition, maintenance burden from complex state machine, and failure to meet the "simple enough to understand in a day" PRD requirement.

## Summary

This proposal simplifies the overly complex task status validation system to meet v1 compliance requirements while maintaining correctness and improving performance.

## What Changes
- Replace complex validation logic with simplified O(1) set-based validation
- Reduce validation code from 300+ lines to <50 lines
- Improve performance by ≥40% for status transition checks
- Update Task model with simplified status transition methods
- Modify core and storage integration to use simplified validation
- Add comprehensive tests for new validation rules
- **BREAKING**: Some previously allowed invalid transitions will be rejected

## Problem Statement

The current implementation has over-engineered task status validation that violates v1 goals:

1. **Excessive Complexity**: Status validation logic is unnecessarily complex for v1 requirements
2. **Performance Impact**: Complex validation adds overhead to every status transition
3. **Maintenance Burden**: Complex state machine is hard to understand and maintain
4. **PRD Violation**: Doesn't meet the "simple enough to understand in a day" goal

## Current State Analysis

The existing status validation includes:
- Complex state transition matrices
- Overly permissive transition rules
- Redundant validation checks
- Performance bottlenecks in status updates

## Proposed Solution

### 1. Simplified Status Transition Rules

Implement a minimal, intuitive state machine:

```python
VALID_TRANSITIONS = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.CANCELLED},  # For retries
    TaskStatus.COMPLETED: set(),  # Terminal state
    TaskStatus.CANCELLED: set(),  # Terminal state
}
```

### 2. Streamlined Validation Function

Replace complex validation with simple, fast checks:

```python
def is_valid_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """Check if status transition is valid."""
    if from_status == to_status:
        return True  # No-op transitions are allowed
    
    return to_status in VALID_TRANSITIONS.get(from_status, set())
```

### 3. Performance Optimizations

- Remove redundant validation calls
- Cache transition validation results
- Use set-based lookups for O(1) performance
- Eliminate complex conditional logic

## Impact Analysis

### Benefits
- **Simplicity**: Reduces complexity by ~70%
- **Performance**: Improves status transition performance by ~50%
- **Maintainability**: Easier to understand and modify
- **PRD Compliance**: Meets v1 simplicity requirements
- **Correctness**: Maintains all essential validation rules

### Risks
- **Behavior Changes**: Some previously allowed transitions will be disallowed
- **Edge Cases**: Need to ensure all valid use cases are preserved

## Alternatives Considered

1. **Keep Current System**: Violates PRD simplicity requirements
2. **Remove All Validation**: Too permissive, could lead to inconsistent states
3. **External State Machine Library**: Over-engineering for v1 needs

## Implementation Plan

See `tasks.md` for detailed implementation steps.

## Success Criteria

- [ ] Status validation simplified to <50 lines of code
- [ ] Performance improved by at least 40%
- [ ] All essential transitions preserved
- [ ] No breaking changes for valid use cases
- [ ] Tests pass with new validation rules

## Files to Change

### Modified Files
- `src/omniq/models.py` - Simplify status validation logic
- `src/omniq/core.py` - Update status transition handling
- `src/omniq/storage/*.py` - Update storage validation if needed

### Test Files
- Update existing tests to match new validation rules
- Add performance tests for status transitions

## Testing Strategy

### Unit Tests
- Test all valid status transitions
- Test invalid transitions are rejected
- Test performance improvements
- Test edge cases and boundary conditions

### Integration Tests
- Test end-to-end status transitions in real workflows
- Test retry scenarios with simplified validation
- Test concurrent status updates

### Regression Tests
- Ensure existing functionality continues to work
- Verify no breaking changes for valid use cases

## Documentation Updates

- Update status transition documentation
- Add simplified state machine diagram
- Update API documentation with new validation rules
- Add migration guide for any behavior changes

## OpenSpec Validation

```bash
openspec validate --strict
```

## Approval

- [ ] Technical review completed
- [ ] Performance improvements verified
- [ ] Backward compatibility confirmed
- [ ] Tests passing
- [ ] Documentation updated

---

**Change ID**: `simplify-task-status-transitions`  
**Date**: 2025-12-01  
**Priority**: HIGH (PRD compliance)  
**Breaking Change**: Minor (some invalid transitions will be rejected)