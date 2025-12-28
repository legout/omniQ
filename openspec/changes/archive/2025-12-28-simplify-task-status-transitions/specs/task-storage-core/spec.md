# OpenSpec: Simplified Task Status Transitions Specification

## Overview

This specification defines a simplified task status validation system that meets v1 compliance requirements while maintaining correctness and improving performance.

## MODIFIED Requirements

### Requirement: Simplified State Validation
The system SHALL replace complex validation with simple, fast state transition checks. Validation MUST achieve O(1) performance and MUST support all required state transitions.

#### Scenario: Simplified State Validation
```python
# Should validate transitions with O(1) performance
assert is_valid_transition(TaskStatus.PENDING, TaskStatus.RUNNING) == True
assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED) == True
assert is_valid_transition(TaskStatus.FAILED, TaskStatus.PENDING) == True  # Retry
assert is_valid_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING) == False  # Terminal
```

#### Scenario: Performance Requirements
```python
# Validation should be fast (<0.001ms per check)
import time
start = time.perf_counter()
for _ in range(10000):
    is_valid_transition(TaskStatus.PENDING, TaskStatus.RUNNING)
duration = time.perf_counter() - start
assert duration < 0.01  # Less than 0.01ms for 10k checks
```

### Requirement: Performance and Simplicity
The validation system MUST meet performance requirements with validation under 0.001ms per check. The implementation SHALL be simple and readable with under 50 lines of code.

#### Scenario: Code Simplicity
```python
# Validation logic should be simple and readable
def is_valid_transition(from_status, to_status):
    if from_status == to_status:
        return True
    return to_status in VALID_TRANSITIONS.get(from_status, set())

# Should be under 50 lines total including comments and type hints
```

## REMOVED Requirements

### Complex Validation Logic

Remove overly complex validation functions that don't provide essential value.

#### Scenario: Removed Complexity
```python
# Old complex validation (REMOVED):
def validate_complex_transition(task, new_status, context, metadata, ...):
    # 100+ lines of complex logic
    pass

# New simple validation (ADDED):
def is_valid_transition(from_status, to_status):
    return to_status in VALID_TRANSITIONS.get(from_status, set())
```

## Current State Analysis

### Existing Issues

1. **Over-Complex Validation**: Multiple nested validation functions
2. **Performance Bottlenecks**: Redundant checks and complex conditionals
3. **Maintenance Burden**: Hard to understand state machine logic
4. **PRD Violation**: Doesn't meet simplicity requirements

### Current Transition Rules (Overly Permissive)

The current implementation allows too many transitions, making the state machine confusing and error-prone.

## Proposed Solution

### Simplified State Machine

```python
from enum import Enum
from typing import Set, Dict

class TaskStatus(Enum):
    """Simplified task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Simplified transition matrix - O(1) set lookups
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.CANCELLED},  # For retries
    TaskStatus.COMPLETED: set(),  # Terminal state
    TaskStatus.CANCELLED: set(),  # Terminal state
}
```

### Streamlined Validation Function

```python
def is_valid_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    """
    Check if status transition is valid.
    
    Args:
        from_status: Current task status
        to_status: Desired new status
        
    Returns:
        True if transition is valid, False otherwise
    """
    # No-op transitions are always allowed
    if from_status == to_status:
        return True
    
    # Check if transition is in the valid set
    return to_status in VALID_TRANSITIONS.get(from_status, set())

def validate_transition(from_status: TaskStatus, to_status: TaskStatus) -> None:
    """
    Validate status transition and raise error if invalid.
    
    Args:
        from_status: Current task status
        to_status: Desired new status
        
    Raises:
        ValueError: If transition is invalid
    """
    if not is_valid_transition(from_status, to_status):
        raise ValueError(
            f"Invalid status transition: {from_status.value} → {to_status.value}. "
            f"Valid transitions from {from_status.value}: "
            f"{[s.value for s in VALID_TRANSITIONS.get(from_status, set())]}"
        )
```

### Task Model Integration

```python
@dataclass
class Task:
    # ... existing fields ...
    
    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if task can transition to new status."""
        return is_valid_transition(self.status, new_status)
    
    def transition_to(self, new_status: TaskStatus) -> None:
        """Transition task to new status with validation."""
        validate_transition(self.status, new_status)
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
    
    @property
    def can_retry(self) -> bool:
        """Check if failed task can be retried."""
        return self.status == TaskStatus.FAILED
    
    def retry(self) -> None:
        """Retry a failed task."""
        if not self.can_retry:
            raise ValueError(f"Cannot retry task in status: {self.status.value}")
        self.transition_to(TaskStatus.PENDING)
```

## Implementation Details

### Performance Optimizations

1. **Set-Based Lookups**: O(1) performance for transition validation
2. **Early Returns**: Fast path for no-op transitions
3. **Minimal Validation**: Only essential checks performed
4. **Cached Results**: Transition matrix is immutable and cached

### Error Handling

```python
class InvalidStatusTransitionError(ValueError):
    """Raised when an invalid status transition is attempted."""
    
    def __init__(self, from_status: TaskStatus, to_status: TaskStatus):
        valid_transitions = [s.value for s in VALID_TRANSITIONS.get(from_status, set())]
        super().__init__(
            f"Invalid status transition: {from_status.value} → {to_status.value}. "
            f"Valid transitions from {from_status.value}: {valid_transitions}"
        )
```

### Integration Points

1. **Core Integration**: Use `validate_transition()` in status updates
2. **Worker Integration**: Check `can_transition_to()` before updates
3. **Storage Integration**: Validate transitions before persistence
4. **API Integration**: Provide clear error messages for invalid transitions

## State Machine Diagram

```
    PENDING
      ↓
   RUNNING
   ↙ ↓ ↘
FAILED COMPLETED CANCELLED
  ↓
PENDING (retry)
```

## Testing Requirements

### Unit Tests

1. **Valid Transitions**: Test all allowed state transitions
2. **Invalid Transitions**: Test rejection of invalid transitions
3. **Performance**: Benchmark validation performance
4. **Edge Cases**: Test no-op transitions and terminal states
5. **Error Messages**: Verify clear error messages

### Integration Tests

1. **Core Integration**: Test status updates in core workflows
2. **Worker Integration**: Test worker status transitions
3. **Storage Integration**: Test persistence with validation
4. **Retry Scenarios**: Test failed task retry logic
5. **Concurrent Updates**: Test concurrent status changes

### Performance Tests

1. **Validation Speed**: Measure O(1) performance
2. **Memory Usage**: Verify minimal memory overhead
3. **Concurrent Load**: Test performance under load
4. **Comparison**: Benchmark against current implementation

## Migration Guide

### Behavior Changes

1. **Stricter Validation**: Some previously allowed transitions will be rejected
2. **Clearer Errors**: Better error messages for invalid transitions
3. **Performance**: Significant improvement in validation speed

### Breaking Changes

1. **Invalid Transitions**: Code relying on overly permissive transitions may break
2. **Error Types**: Different exception type for invalid transitions

### Migration Steps

1. **Audit Current Usage**: Identify any invalid transitions in use
2. **Update Code**: Fix any invalid transition attempts
3. **Handle New Errors**: Update error handling for new exception types
4. **Test Thoroughly**: Verify all workflows work with new validation

## Security Considerations

1. **State Consistency**: Validation prevents inconsistent task states
2. **Race Conditions**: Proper handling of concurrent status updates
3. **Error Information**: Error messages don't expose sensitive data

## Future Extensions

1. **Custom Transitions**: Allow configuration of additional transitions
2. **Transition Hooks**: Add callbacks for status changes
3. **Audit Trail**: Log all status transitions for debugging
4. **State Metrics**: Track transition patterns for optimization

## Success Criteria

- [ ] Validation logic <50 lines of code
- [ ] Performance improvement ≥40%
- [ ] All essential transitions preserved
- [ ] Clear error messages for invalid transitions
- [ ] No breaking changes for valid use cases
- [ ] Comprehensive test coverage
- [ ] Documentation updated and accurate