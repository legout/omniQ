# Worker Compatibility Fix Specification

## MODIFIED Requirements

### Requirement: AsyncWorkerPool Constructor Parameters
AsyncWorkerPool constructor SHALL support both the new `queue` parameter and the legacy `storage` parameter to maintain backward compatibility while encouraging migration to the new interface.

**Current Signature**: `__init__(self, queue: AsyncTaskQueue, max_workers: int = 1)`

**Target Signature**: `__init__(self, queue: AsyncTaskQueue | None = None, storage: BaseStorage | None = None, max_workers: int = 1, logger: Logger | None = None)`

#### Scenario: New Interface Usage
```python
# New recommended interface
queue = AsyncTaskQueue(storage=storage)
worker = AsyncWorkerPool(queue=queue, max_workers=4)
assert worker.queue == queue
```

#### Scenario: Legacy Interface Usage
```python
# Legacy interface with deprecation warning
with pytest.warns(DeprecationWarning):
    worker = AsyncWorkerPool(storage=storage, max_workers=4)
    assert worker.queue.storage == storage
```

#### Scenario: Parameter Validation Error
```python
# Error when both parameters provided
queue = AsyncTaskQueue(storage=storage)
with pytest.raises(ValueError, match="Cannot provide both"):
    AsyncWorkerPool(queue=queue, storage=storage)
```

### Requirement: Parameter Validation Logic
AsyncWorkerPool MUST include comprehensive parameter validation that ensures exactly one of `queue` or `storage` is provided, with clear error messages for invalid combinations.

#### Scenario: No Parameters Error
```python
# Error when no parameters provided
with pytest.raises(ValueError, match="Either 'queue' or 'storage'"):
    AsyncWorkerPool()
```

#### Scenario: Type Validation
```python
# Error for invalid types
with pytest.raises(TypeError, match="'queue' must be AsyncTaskQueue"):
    AsyncWorkerPool(queue="invalid")

with pytest.raises(TypeError, match="'storage' must be BaseStorage"):
    AsyncWorkerPool(storage="invalid")
```

## ADDED Requirements

### Requirement: Deprecation Warning System
AsyncWorkerPool SHALL emit deprecation warnings when the legacy `storage` parameter is used, providing clear migration guidance to users.

#### Scenario: Deprecation Warning Emission
```python
# Legacy usage triggers warning
storage = MockStorage()
with pytest.warns(DeprecationWarning) as warning:
    worker = AsyncWorkerPool(storage=storage)
    assert "deprecated" in str(warning[0].message).lower()
    assert "queue" in str(warning[0].message)
```

#### Scenario: Warning Message Content
```python
# Warning should include helpful migration info
storage = MockStorage()
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    worker = AsyncWorkerPool(storage=storage)
    assert len(w) == 1
    assert "Use 'queue' parameter instead" in str(w[0].message)
```

### Requirement: Internal Queue Creation
AsyncWorkerPool MUST provide internal queue creation capability when using the legacy `storage` parameter, automatically creating an AsyncTaskQueue instance.

#### Scenario: Automatic Queue Creation
```python
# Queue should be created automatically from storage
storage = MockStorage()
worker = AsyncWorkerPool(storage=storage)
assert isinstance(worker.queue, AsyncTaskQueue)
assert worker.queue.storage == storage
```

#### Scenario: Queue Creation with Logger
```python
# Logger should be passed to created queue
storage = MockStorage()
logger = get_logger()
worker = AsyncWorkerPool(storage=storage, logger=logger)
assert worker.queue.logger == logger
```

### Requirement: AsyncOmniQ Integration Update
AsyncOmniQ SHALL be updated to use the new AsyncWorkerPool interface, passing the queue parameter instead of relying on legacy behavior.

#### Scenario: Core Integration
```python
# AsyncOmniQ should use new interface
storage = MockStorage()
config = OmniQConfig()
omniq = AsyncOmniQ(storage=storage, config=config)

# Should work with new internal structure
task = await omniq.add_task(lambda: "test")
result = await omniq.get_result(task.id)
assert result == "test"
```

## REMOVED Requirements

### Requirement: Queue-Only Constructor
Remove the queue-only constructor signature that requires `queue: AsyncTaskQueue` as a mandatory parameter. The constructor SHALL be modified to make `queue` optional and add the legacy `storage` parameter.

#### Scenario: Constructor Signature Removal
```python
# This constructor signature should be removed
def __init__(self, queue: AsyncTaskQueue, max_workers: int = 1):
    # REMOVED - replaced with backward compatible version
```