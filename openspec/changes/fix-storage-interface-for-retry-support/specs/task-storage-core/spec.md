# Storage Interface Enhancement for Retry Support

## ADDED Requirements

### Requirement: BaseStorage.get_task() Method
Add abstract `get_task()` method to BaseStorage interface. Storage backends must provide ability to retrieve a task by its unique identifier.

**Signature**: `async def get_task(self, task_id: str) -> Optional[Task]`

**Returns**: Task object if found, None if not found

**Exceptions**: Must raise StorageError if retrieval operation fails

#### Scenario: Task Retrieval for Retry Logic
```python
# When AsyncTaskQueue needs to retry a failed task
storage = SQLiteStorage()
task = await storage.get_task("task-123")
assert task is not None
assert task.id == "task-123"
assert task.attempts < task.max_retries
```

#### Scenario: Task Retrieval for Interval Rescheduling
```python
# When AsyncTaskQueue needs to reschedule an interval task
storage = FileStorage()
task = await storage.get_task("interval-task-456")
assert task is not None
assert task.schedule is not None
```

### Requirement: BaseStorage.reschedule() Method
Add abstract `reschedule()` method to BaseStorage interface. Storage backends must provide ability to update a task's ETA for retry or interval execution.

**Signature**: `async def reschedule(self, task_id: str, new_eta: datetime) -> None`

**Parameters**: 
- `task_id`: Unique task identifier to reschedule
- `new_eta`: New execution time in UTC

**Exceptions**: 
- Must raise NotFoundError if task doesn't exist
- Must raise StorageError if update operation fails

#### Scenario: Retry Task Rescheduling
```python
# When AsyncTaskQueue retries a failed task after delay
storage = SQLiteStorage()
retry_eta = datetime.now(timezone.utc) + timedelta(seconds=30)
await storage.reschedule("failed-task-789", retry_eta)
# Task should now be PENDING with new ETA
```

#### Scenario: Interval Task Rescheduling
```python
# When AsyncTaskQueue reschedules a recurring interval task
storage = FileStorage()
next_run = datetime.now(timezone.utc) + timedelta(minutes=5)
await storage.reschedule("interval-task-101", next_run)
# Task should now be PENDING with next interval time
```

## MODIFIED Requirements

### AsyncTaskQueue.complete_task() Method
- **Requirement**: Update complete_task() to use storage.get_task() instead of fallback
- **Description**: Remove the _get_task_by_id() fallback that always returns None
- **Impact**: Retry and interval logic will now work correctly with proper task retrieval

#### Scenario: Task Completion with Retry Logic
```python
# When completing a task that may need retry
queue = AsyncTaskQueue(storage)
await queue.complete_task("task-123", result=None, task=None)
# Should fetch task from storage and handle retry/interval logic
```

#### Scenario: Task Completion with Provided Task Object
```python
# When task object is already available (optimization)
queue = AsyncTaskQueue(storage)
task = await storage.get_task("task-123")
await queue.complete_task("task-123", result="success", task=task)
# Should use provided task object without additional storage call
```

### Storage Backend Implementations
- **Requirement**: All storage backends must implement the new abstract methods
- **Description**: FileStorage and SQLiteStorage need concrete implementations
- **Impact**: Ensures consistent behavior across all storage backends

#### Scenario: FileStorage Implementation
```python
# FileStorage must implement new methods with file locking
storage = FileStorage("/tmp/tasks")
task = await storage.get_task("file-task-1")
await storage.reschedule("file-task-1", datetime.now(timezone.utc))
```

#### Scenario: SQLiteStorage Implementation
```python
# SQLiteStorage must implement new methods with proper SQL
storage = SQLiteStorage("/tmp/tasks.db")
task = await storage.get_task("sqlite-task-1")
await storage.reschedule("sqlite-task-1", datetime.now(timezone.utc))
```

## REMOVED Requirements

### AsyncTaskQueue._get_task_by_id() Fallback Method
- **Requirement**: Remove the fallback method that always returns None
- **Description**: This method was a workaround that broke retry functionality
- **Impact**: AsyncTaskQueue will now properly use storage interface methods

#### Scenario: Fallback Removal
```python
# This method should be removed from AsyncTaskQueue
async def _get_task_by_id(self, task_id: str) -> Optional[Task]:
    return None  # This broke retry logic
```