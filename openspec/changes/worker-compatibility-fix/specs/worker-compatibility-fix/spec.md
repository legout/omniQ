# Worker Compatibility Fix Specification

## Overview

Restore backward compatibility in AsyncWorkerPool constructor while supporting new AsyncTaskQueue interface.

## Current State

```python
# src/omniq/worker.py (current - breaking)
class AsyncWorkerPool:
    def __init__(self, queue: AsyncTaskQueue, max_workers: int = 1):
        self.queue = queue
        # ... rest of initialization
```

## Target State

```python
# src/omniq/worker.py (target - backward compatible)
class AsyncWorkerPool:
    def __init__(
        self,
        queue: AsyncTaskQueue | None = None,
        storage: BaseStorage | None = None,
        max_workers: int = 1,
        logger: Logger | None = None
    ):
        # Handle both interfaces
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

## Detailed Changes

### 1. Constructor Parameter Changes

#### Parameter Addition
```python
# New parameters for backward compatibility
queue: AsyncTaskQueue | None = None      # New interface
storage: BaseStorage | None = None       # Old interface (deprecated)
logger: Logger | None = None             # Optional logger
```

#### Parameter Validation
```python
def _validate_parameters(self, queue, storage):
    """Validate and normalize constructor parameters."""
    if queue is None and storage is None:
        raise ValueError("Either 'queue' or 'storage' must be provided")
    
    if queue is not None and storage is not None:
        raise ValueError("Cannot provide both 'queue' and 'storage'")
    
    return queue or AsyncTaskQueue(storage=storage)
```

### 2. Deprecation Handling

#### Warning System
```python
import warnings
from functools import wraps

def deprecated_storage_param(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if 'storage' in kwargs and kwargs['storage'] is not None:
            warnings.warn(
                "The 'storage' parameter is deprecated. "
                "Use 'queue' parameter with AsyncTaskQueue instead.",
                DeprecationWarning,
                stacklevel=2
            )
        return func(self, *args, **kwargs)
    return wrapper
```

### 3. Internal Queue Creation

#### Queue Factory
```python
def _create_queue_from_storage(self, storage: BaseStorage) -> AsyncTaskQueue:
    """Create AsyncTaskQueue from BaseStorage for backward compatibility."""
    logger = self.logger or get_logger()
    return AsyncTaskQueue(storage=storage, logger=logger)
```

### 4. Core Integration Updates

#### AsyncOmniQ Integration
```python
# core.py - Update to use new interface
class AsyncOmniQ:
    def __init__(self, storage: BaseStorage, config: OmniQConfig):
        self.storage = storage
        self.config = config
        self.queue = AsyncTaskQueue(storage=storage)
        self.worker = AsyncWorkerPool(queue=self.queue)  # New interface
```

## Implementation Steps

### Step 1: Update Constructor
1. Add new parameters with proper type hints
2. Add parameter validation logic
3. Implement backward compatibility handling

### Step 2: Add Deprecation Warnings
1. Implement warning system
2. Add helpful migration messages
3. Document deprecation timeline

### Step 3: Update Core Integration
1. Update AsyncOmniQ to use new interface
2. Ensure internal consistency
3. Update any other internal uses

### Step 4: Add Comprehensive Tests
1. Test both interfaces work
2. Test deprecation warnings
3. Test error conditions

## Migration Path

### Phase 1: Dual Interface (Current Release)
- Both interfaces work
- Deprecation warnings for old interface
- Documentation updates

### Phase 2: Warning Escalation (Next Minor Release)
- Deprecation warnings become more prominent
- Documentation emphasizes migration
- Examples use new interface only

### Phase 3: Removal (v2.0)
- Old interface removed
- Breaking change with clear migration guide
- Full documentation update

## Testing Requirements

### Constructor Tests
```python
def test_worker_new_interface():
    """Test new queue interface."""
    storage = MockStorage()
    queue = AsyncTaskQueue(storage=storage)
    worker = AsyncWorkerPool(queue=queue)
    assert worker.queue == queue

def test_worker_old_interface():
    """Test old storage interface with deprecation warning."""
    storage = MockStorage()
    with pytest.warns(DeprecationWarning) as warning:
        worker = AsyncWorkerPool(storage=storage)
        assert worker.queue.storage == storage
        assert "deprecated" in str(warning[0].message)

def test_worker_both_parameters_error():
    """Test error when both parameters provided."""
    storage = MockStorage()
    queue = AsyncTaskQueue(storage=storage)
    with pytest.raises(ValueError, match="both 'queue' and 'storage'"):
        AsyncWorkerPool(queue=queue, storage=storage)

def test_worker_no_parameters_error():
    """Test error when no parameters provided."""
    with pytest.raises(ValueError, match="Either 'queue' or 'storage'"):
        AsyncWorkerPool()
```

### Integration Tests
```python
async def test_omniq_integration():
    """Test AsyncOmniQ works with new internal structure."""
    storage = MockStorage()
    config = OmniQConfig()
    omniq = AsyncOmniQ(storage=storage, config=config)
    
    # Should work seamlessly
    task = await omniq.add_task(lambda: "test")
    result = await omniq.get_result(task.id)
    assert result == "test"

async def test_worker_task_execution():
    """Test worker can execute tasks with both interfaces."""
    storage = MockStorage()
    
    # New interface
    queue = AsyncTaskQueue(storage=storage)
    worker1 = AsyncWorkerPool(queue=queue)
    
    # Old interface
    worker2 = AsyncWorkerPool(storage=storage)
    
    # Both should work identically
    for worker in [worker1, worker2]:
        task = await worker.queue.add_task(lambda: "test")
        result = await worker.queue.get_result(task.id)
        assert result == "test"
```

## Error Handling

### Parameter Validation Errors
```python
# Clear error messages for common mistakes
if queue is not None and storage is not None:
    raise ValueError(
        "Cannot provide both 'queue' and 'storage' parameters. "
        "Use 'queue' with AsyncTaskQueue for new code, "
        "or 'storage' with BaseStorage for legacy code."
    )

if queue is None and storage is None:
    raise ValueError(
        "Either 'queue' or 'storage' parameter must be provided. "
        "Recommended: queue=AsyncTaskQueue(storage=storage)"
    )
```

### Type Validation
```python
def _validate_types(self, queue, storage):
    """Validate parameter types."""
    if queue is not None and not isinstance(queue, AsyncTaskQueue):
        raise TypeError(f"'queue' must be AsyncTaskQueue, got {type(queue)}")
    
    if storage is not None and not isinstance(storage, BaseStorage):
        raise TypeError(f"'storage' must be BaseStorage, got {type(storage)}")
```

## Performance Considerations

### Minimal Overhead
- Parameter validation is O(1)
- Queue creation only when needed
- No impact on new interface performance

### Memory Efficiency
- No duplicate objects created
- Shared queue reference
- Efficient parameter handling

## Documentation Updates

### API Documentation
```python
class AsyncWorkerPool:
    """Pool of async workers for task execution.
    
    Args:
        queue: AsyncTaskQueue for task management (recommended)
        storage: BaseStorage for task management (deprecated)
        max_workers: Maximum number of concurrent workers
        logger: Optional logger instance
        
    Note:
        The 'storage' parameter is deprecated and will be removed in v2.0.
        Use 'queue' parameter with AsyncTaskQueue instead.
        
    Examples:
        # New interface (recommended)
        queue = AsyncTaskQueue(storage=storage)
        worker = AsyncWorkerPool(queue=queue)
        
        # Old interface (deprecated)
        worker = AsyncWorkerPool(storage=storage)
    """
```

### Migration Guide
```markdown
## Migrating from Storage to Queue Interface

### Before (v1.x - deprecated)
```python
worker = AsyncWorkerPool(storage=storage, max_workers=4)
```

### After (v1.x - recommended)
```python
queue = AsyncTaskQueue(storage=storage)
worker = AsyncWorkerPool(queue=queue, max_workers=4)
```

### Or through AsyncOmniQ (easiest)
```python
omniq = AsyncOmniQ(storage=storage, config=config)
# worker and queue created automatically
```
```

## Future Compatibility

### v2.0 Planning
- Remove `storage` parameter entirely
- Remove deprecation warning system
- Simplify constructor to new interface only
- Update all documentation

### Migration Timeline
- v1.x: Dual interface with warnings
- v1.x+1: Escalated warnings
- v2.0: Breaking change with migration guide