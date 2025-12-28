# Fix Storage Interface for Retry Support

## Problem Statement

The AsyncTaskQueue implementation requires storage methods that don't exist in the BaseStorage interface:

1. **Missing `get_task()` method**: AsyncTaskQueue needs to retrieve task information for retry and interval logic
2. **Missing `reschedule()` method**: AsyncTaskQueue calls this method for retry scheduling
3. **Fallback to `_get_task_by_id()`**: Always returns `None`, causing retry logic to fail

## Impact

- **Retry logic broken**: Tasks cannot be properly retried due to missing task retrieval
- **Interval tasks broken**: Cannot reschedule recurring tasks
- **Storage abstraction weakened**: AsyncTaskQueue has to work around missing methods
- **Future extensibility limited**: New backends won't know what methods to implement

## Solution

### 1. Add Missing Methods to BaseStorage

```python
# src/omniq/storage/base.py
class BaseStorage(ABC):
    # ... existing methods ...
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            Task if found, None otherwise
            
        Raises:
            StorageError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """
        Update a task's ETA for retry or interval rescheduling.
        
        Args:
            task_id: Unique task identifier
            new_eta: New execution time
            
        Raises:
            NotFoundError: If task doesn't exist
            StorageError: If update fails
        """
        pass
```

### 2. Update SQLiteStorage Implementation

```python
# src/omniq/storage/sqlite.py
class SQLiteStorage(BaseStorage):
    # ... existing methods ...
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve task by ID from SQLite database."""
        conn = await self._get_connection()
        
        cursor = await conn.execute(
            """
            SELECT id, func_path, args, kwargs, status, schedule, eta,
                   max_retries, timeout, attempts, created_at, updated_at, last_attempt_at
            FROM tasks 
            WHERE id = ?
            """,
            (task_id,)
        )
        
        row = await cursor.fetchone()
        if row is None:
            return None
            
        return self._row_to_task(row)
    
    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Update task ETA for retry or interval execution."""
        conn = await self._get_connection()
        
        eta_str = self._serialize_datetime(new_eta)
        
        try:
            await conn.execute(
                """
                UPDATE tasks 
                SET eta = ?, status = 'PENDING', updated_at = ?
                WHERE id = ?
                """,
                (eta_str, self._serialize_datetime(datetime.now(timezone.utc)), task_id)
            )
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to reschedule task {task_id}: {e}")
```

### 3. Remove Fallback Methods

```python
# src/omniq/queue.py
class AsyncTaskQueue:
    # Remove these methods:
    # async def _get_task_by_id(self, task_id: str) -> Optional[Task]:
    #     return None  # Always returns None
    
    # Update complete_task() to use storage.get_task() directly
    async def complete_task(self, task_id: str, result: Optional[Any] = None, task: Optional[Task] = None) -> None:
        if task is None:
            task = await self.storage.get_task(task_id)
            if task is None:
                self.logger.warning(f"Task not found for completion: {task_id}")
                return
        
        # ... rest of implementation unchanged
```

## Benefits

- **Fixes retry logic**: Tasks can be properly retrieved and retried
- **Fixes interval tasks**: Recurring tasks work correctly
- **Strengthens storage abstraction**: Clear interface contract
- **Enables future backends**: Redis, PostgreSQL implementations know what to implement
- **Removes fragile workarounds**: No more hardcoded `None` returns

## Testing

- Add tests for `get_task()` method in existing test suites
- Add tests for `reschedule()` method in existing test suites
- Verify retry logic works with real storage operations
- Verify interval task rescheduling works end-to-end

## Backward Compatibility

- **Fully backward compatible**: Existing code continues to work
- **No API changes**: Only adds missing functionality
- **Optional usage**: AsyncTaskQueue gracefully handles cases where task is passed directly

## Implementation Order

1. Update BaseStorage interface
2. Update SQLiteStorage implementation  
3. Update FileStorage implementation
4. Remove fallback methods from AsyncTaskQueue
5. Update tests
6. Verify all functionality works

This change is critical for the AsyncTaskQueue implementation to work correctly and fulfill the v1 requirements.