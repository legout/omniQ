# Task Interval Type Fix Specification

## MODIFIED Requirements

### Requirement: Task.interval Field Type
Task model SHALL change the `interval` field type from `int` to `timedelta | None` to comply with v1 specification requirements.

**Current State**: `interval: int = 0`

**Target State**: `interval: timedelta | None = None`

#### Scenario: Task Creation with Timedelta Interval
```python
# Create task with proper timedelta interval
task = Task(
    func=lambda: "test",
    interval=timedelta(seconds=30)
)
assert isinstance(task.interval, timedelta)
assert task.interval.total_seconds() == 30
```

#### Scenario: Task Creation with Integer Interval (Backward Compatibility)
```python
# Create task with int interval (should be converted)
task = Task(func=lambda: "test", interval=30)
assert isinstance(task.interval, timedelta)
assert task.interval.total_seconds() == 30
```

### Requirement: Task Interval Field Validation
Task model MUST include a field validator that accepts both `timedelta` and `int` types for backward compatibility, converting `int` values to `timedelta` internally.

#### Scenario: Integer to Timedelta Conversion
```python
# Integer intervals should be converted to timedelta seconds
task = Task(func=lambda: "test", interval=60)
assert isinstance(task.interval, timedelta)
assert task.interval.total_seconds() == 60
```

#### Scenario: Invalid Interval Type Rejection
```python
# Invalid types should raise ValueError
with pytest.raises(ValueError, match="interval must be timedelta or int"):
    Task(func=lambda: "test", interval="invalid")
```

## ADDED Requirements

### Requirement: Timedelta Serialization Support
Serialization module SHALL add support for serializing and deserializing `timedelta` objects to ensure proper persistence of interval tasks.

#### Scenario: Timedelta Serialization
```python
# Serialize timedelta to dict format
interval = timedelta(minutes=5, seconds=30)
serialized = serialize_timedelta(interval)
assert serialized['type'] == 'timedelta'
assert serialized['total_seconds'] == 330.0
```

#### Scenario: Timedelta Deserialization
```python
# Deserialize timedelta from dict format
data = {'type': 'timedelta', 'total_seconds': 330.0}
interval = deserialize_timedelta(data)
assert isinstance(interval, timedelta)
assert interval.total_seconds() == 330.0
```

### Requirement: AsyncTaskQueue Interval Handling
AsyncTaskQueue SHALL properly handle both `timedelta` and `int` interval types in `add_interval_task()` method, converting `int` values to `timedelta` internally.

#### Scenario: Interval Task Creation with Timedelta
```python
# Create interval task with timedelta
queue = AsyncTaskQueue(storage)
task = await queue.add_interval_task(
    func=lambda: "test",
    interval=timedelta(minutes=1)
)
assert isinstance(task.interval, timedelta)
```

#### Scenario: Interval Task Creation with Integer
```python
# Create interval task with integer (backward compatibility)
queue = AsyncTaskQueue(storage)
task = await queue.add_interval_task(
    func=lambda: "test",
    interval=60  # seconds
)
assert isinstance(task.interval, timedelta)
assert task.interval.total_seconds() == 60
```

## REMOVED Requirements

### Requirement: Integer Interval Field Type
Remove the `interval: int = 0` field definition from Task model. The integer-only interval type SHALL be replaced with `timedelta | None = None` to support proper time interval handling.

#### Scenario: Integer Interval Removal
```python
# This field definition should be removed
class Task(BaseModel):
    interval: int = 0  # REMOVED
```