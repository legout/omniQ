# Task Interval Type Fix Specification

## Overview

Fix critical type inconsistency in Task model where `interval` field is defined as `int` but v1 spec requires `timedelta`.

## Current State

```python
# src/omniq/models.py (current)
class Task(BaseModel):
    # ... other fields ...
    interval: int = 0  # WRONG: Should be timedelta
```

## Target State

```python
# src/omniq/models.py (target)
class Task(BaseModel):
    # ... other fields ...
    interval: timedelta | None = None  # CORRECT: timedelta type
```

## Detailed Changes

### 1. Task Model Updates

#### Field Type Change
```python
# Before
interval: int = 0

# After  
interval: timedelta | None = None
```

#### Validation Updates
```python
@field_validator('interval', mode='before')
def validate_interval(cls, v):
    if v is None:
        return None
    if isinstance(v, int):
        return timedelta(seconds=v)
    if isinstance(v, timedelta):
        return v
    raise ValueError("interval must be timedelta or int (seconds)")
```

### 2. Serialization Updates

#### Timedelta Serialization
```python
# serialization.py - Add timedelta support
def serialize_timedelta(td: timedelta) -> dict:
    return {
        'type': 'timedelta',
        'total_seconds': td.total_seconds()
    }

def deserialize_timedelta(data: dict) -> timedelta:
    if data.get('type') == 'timedelta':
        return timedelta(seconds=data['total_seconds'])
    raise ValueError("Invalid timedelta data")
```

### 3. AsyncTaskQueue Updates

#### Interval Task Creation
```python
# queue.py - Fix interval handling
async def add_interval_task(
    self,
    func: Callable,
    interval: timedelta | int,
    *args,
    **kwargs
) -> Task:
    # Convert int to timedelta if needed
    if isinstance(interval, int):
        interval = timedelta(seconds=interval)
    
    # Create task with proper interval type
    task = Task(
        func=func,
        args=args,
        kwargs=kwargs,
        interval=interval,  # Now correct type
        # ... other fields
    )
```

## Implementation Steps

### Step 1: Update Task Model
1. Change interval field type to `timedelta | None`
2. Add field validator for backward compatibility
3. Update default value to `None`

### Step 2: Update Serialization
1. Add timedelta serialization functions
2. Update Task serialization to handle interval
3. Update Task deserialization to handle interval

### Step 3: Update AsyncTaskQueue
1. Fix interval task creation method
2. Add interval conversion utilities
3. Update interval scheduling logic

### Step 4: Update Tests
1. Update Task model tests
2. Add interval serialization tests
3. Update AsyncTaskQueue tests

## Migration Considerations

### Data Migration
- Existing tasks with `interval: int` need conversion
- Provide migration script if needed
- Handle backward compatibility gracefully

### API Compatibility
- Accept both `int` and `timedelta` in APIs
- Convert `int` to `timedelta` internally
- Document deprecation of `int` usage

## Testing Requirements

### Unit Tests
```python
def test_task_interval_timedelta():
    task = Task(interval=timedelta(seconds=30))
    assert isinstance(task.interval, timedelta)
    assert task.interval.total_seconds() == 30

def test_task_interval_int_conversion():
    task = Task(interval=30)
    assert isinstance(task.interval, timedelta)
    assert task.interval.total_seconds() == 30

def test_interval_serialization():
    interval = timedelta(seconds=60)
    serialized = serialize_timedelta(interval)
    deserialized = deserialize_timedelta(serialized)
    assert interval == deserialized
```

### Integration Tests
```python
async def test_interval_task_creation():
    queue = AsyncTaskQueue(storage)
    
    # Test with timedelta
    task1 = await queue.add_interval_task(func, timedelta(seconds=30))
    assert isinstance(task1.interval, timedelta)
    
    # Test with int (backward compatibility)
    task2 = await queue.add_interval_task(func, 30)
    assert isinstance(task2.interval, timedelta)
```

## Error Handling

### Validation Errors
- Invalid interval types should raise `ValueError`
- Clear error messages for type mismatches
- Graceful fallback for common cases

### Serialization Errors
- Handle malformed timedelta data
- Provide clear error messages
- Fallback to default values if needed

## Performance Considerations

### Type Conversion
- Minimize conversions in hot paths
- Cache converted values when possible
- Use efficient timedelta operations

### Serialization
- Efficient timedelta serialization format
- Minimize overhead for interval tasks
- Batch operations when possible

## Documentation Updates

### API Documentation
- Update Task model documentation
- Document interval field type change
- Provide migration examples

### Changelog
- Document breaking change
- Provide upgrade path
- Note backward compatibility features