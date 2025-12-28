# Fix Worker Compatibility for Backward Compatibility

## Overview

Restore backward compatibility in AsyncWorkerPool constructor that was broken when AsyncTaskQueue integration required `AsyncTaskQueue` parameter instead of optional `BaseStorage`.

## Problem Statement

**Current Issue:**
- AsyncWorkerPool constructor now requires `AsyncTaskQueue` parameter
- Old code using `BaseStorage` parameter breaks
- Backward compatibility lost
- Migration barrier for existing users

**Impact:**
- Existing user code fails to run
- Breaking change without migration path
- Poor user experience during upgrade

## Root Cause Analysis

The AsyncTaskQueue integration changed worker constructor:
- Before: `AsyncWorkerPool(storage: BaseStorage | None = None)`
- After: `AsyncWorkerPool(queue: AsyncTaskQueue)`
- No backward compatibility provided

## Proposed Solution

### 1. Restore Backward-Compatible Constructor
- Accept both `AsyncTaskQueue` and `BaseStorage` parameters
- Create AsyncTaskQueue internally when BaseStorage provided
- Maintain new interface while supporting old interface

### 2. Deprecation Path
- Mark old interface as deprecated
- Provide clear migration warnings
- Document upgrade path

### 3. Graceful Migration
- Auto-create AsyncTaskQueue when needed
- Log deprecation warnings
- Provide migration guide

## Implementation Plan

### Phase 1: Dual Interface Support
1. Update AsyncWorkerPool constructor
2. Add parameter type detection
3. Create AsyncTaskQueue when BaseStorage provided

### Phase 2: Deprecation Handling
1. Add deprecation warnings
2. Document migration path
3. Update examples and documentation

### Phase 3: Testing and Validation
1. Test both interfaces
2. Validate backward compatibility
3. Test migration scenarios

## Files to Change

### Core Files
- `src/omniq/worker.py` - Update AsyncWorkerPool constructor
- `src/omniq/core.py` - Update AsyncOmniQ worker creation

### Documentation
- Update migration guide
- Add deprecation notices
- Update examples

## Detailed Implementation

### Constructor Changes
```python
class AsyncWorkerPool:
    def __init__(
        self,
        queue: AsyncTaskQueue | None = None,
        storage: BaseStorage | None = None,
        max_workers: int = 1,
        logger: Logger | None = None
    ):
        # Backward compatibility handling
        if queue is None and storage is not None:
            # Old interface - create queue internally
            warnings.warn(
                "Passing 'storage' to AsyncWorkerPool is deprecated. "
                "Use 'queue' parameter instead.",
                DeprecationWarning,
                stacklevel=2
            )
            queue = AsyncTaskQueue(storage=storage)
        elif queue is None:
            raise ValueError("Either 'queue' or 'storage' must be provided")
        
        self.queue = queue
        # ... rest of initialization
```

### Core Integration Updates
```python
# core.py - Update AsyncOmniQ
class AsyncOmniQ:
    def __init__(self, storage: BaseStorage, config: OmniQConfig):
        self.storage = storage
        self.config = config
        self.queue = AsyncTaskQueue(storage=storage)
        self.worker = AsyncWorkerPool(queue=self.queue)  # New interface
```

## Migration Strategy

### For Users
1. **Immediate**: No changes required (backward compatible)
2. **Recommended**: Migrate to new interface
3. **Future**: Old interface will be removed in v2

### Migration Examples
```python
# Old way (still works but deprecated)
worker = AsyncWorkerPool(storage=storage)

# New way (recommended)
queue = AsyncTaskQueue(storage=storage)
worker = AsyncWorkerPool(queue=queue)

# Or through AsyncOmniQ (recommended)
omniq = AsyncOmniQ(storage=storage, config=config)
# worker and queue created automatically
```

## Risk Assessment

**Breaking Changes:**
- None with this approach (backward compatible)

**Risks:**
- Complexity in constructor logic
- Potential confusion with dual interfaces

**Mitigation:**
- Clear documentation
- Helpful deprecation warnings
- Comprehensive testing

## Success Criteria

- [ ] Existing code continues to work without changes
- [ ] New interface works as designed
- [ ] Deprecation warnings displayed appropriately
- [ ] Migration path is clear and documented
- [ ] All tests pass for both interfaces

## Dependencies

- Depends on AsyncTaskQueue implementation (already complete)
- Should be implemented after storage interface fixes
- Independent of task interval type fixes

## Testing Strategy

### Backward Compatibility Tests
```python
def test_worker_old_interface():
    storage = MockStorage()
    worker = AsyncWorkerPool(storage=storage)
    assert worker.queue.storage == storage

def test_worker_new_interface():
    storage = MockStorage()
    queue = AsyncTaskQueue(storage=storage)
    worker = AsyncWorkerPool(queue=queue)
    assert worker.queue == queue

def test_deprecation_warning():
    storage = MockStorage()
    with pytest.warns(DeprecationWarning):
        AsyncWorkerPool(storage=storage)
```

### Integration Tests
```python
async def test_omniq_integration():
    storage = MockStorage()
    config = OmniQConfig()
    omniq = AsyncOmniQ(storage=storage, config=config)
    
    # Should work with new internal structure
    task = await omniq.add_task(some_function)
    result = await omniq.get_result(task.id)
```

## Rollback Plan

If issues arise:
1. Revert to new interface only
2. Document breaking change clearly
3. Provide immediate migration guide
4. Consider rapid patch release

## Alternatives Considered

1. **Breaking change only**: Poor user experience
2. **Separate WorkerV2 class**: Confusing, maintenance overhead
3. **Factory pattern**: Over-engineering for this case

**Chosen approach:** Dual interface with deprecation for smooth migration.