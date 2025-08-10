# Task 2: SQLite Backend, Queue, Result and Event Storage

## Overview

This task involves implementing the SQLite backend for OmniQ, including task queue, result storage, and event storage components. All implementations will follow the "Async First, Sync Wrapped" pattern as specified in the project plan.

## Objectives

1. Implement SQLite-based task queue with support for multiple named queues
2. Implement SQLite-based result storage with TTL support
3. Implement SQLite-based event storage with structured querying
4. Create a unified SQLite backend that provides all three components
5. Ensure proper async/await support using aiosqlite

## Detailed Implementation Plan

### 2.1 SQLite Backend Base (`src/omniq/backends/sqlite.py`)

**Purpose**: Create a unified SQLite backend that provides task queue, result storage, and event storage.

**Implementation Requirements**:
- Use aiosqlite for async database operations
- Implement proper connection management
- Support database initialization and schema creation
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/backends/sqlite.py
import os
import aiosqlite
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from contextlib import asynccontextmanager

from ..base.queue import BaseTaskQueue
from ..base.result_storage import BaseResultStorage
from ..base.event_storage import BaseEventStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent, EventType
from ..models.schedule import Schedule, ScheduleStatus

class SQLiteBackend:
    """Unified SQLite backend for OmniQ."""
    
    def __init__(self, project_name: str, base_dir: str = "./omniq_data", **kwargs):
        self.project_name = project_name
        self.base_dir = Path(base_dir)
        self.db_path = self.base_dir / f"{project_name}.db"
        self._connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
    
    async def initialize_async(self):
        """Initialize the database and create tables."""
        # Create base directory if it doesn't exist
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self._connection = await aiosqlite.connect(self.db_path)
        
        # Enable WAL mode for better concurrency
        await self._connection.execute("PRAGMA journal_mode=WAL")
        
        # Create tables
        await self._create_tables()
    
    async def _create_tables(self):
        """Create all necessary tables."""
        # Tasks table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                queue_name TEXT NOT NULL,
                status TEXT NOT NULL,
                func TEXT NOT NULL,
                func_args TEXT,
                func_kwargs TEXT,
                name TEXT,
                description TEXT,
                tags TEXT,
                priority INTEGER DEFAULT 0,
                run_at TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                ttl TEXT,
                expires_at TEXT,
                depends_on TEXT,
                callback TEXT,
                callback_args TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                retry_delay TEXT,
                result_ttl TEXT,
                store_result BOOLEAN DEFAULT 1
            )
        """)
        
        # Schedules table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                cron_expression TEXT,
                interval TEXT,
                run_at TEXT,
                max_runs INTEGER,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_run_at TEXT,
                next_run_at TEXT,
                run_count INTEGER DEFAULT 0,
                paused_at TEXT,
                resumed_at TEXT,
                name TEXT,
                description TEXT,
                tags TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        """)
        
        # Results table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                error_traceback TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                ttl TEXT,
                expires_at TEXT,
                execution_time REAL,
                worker_id TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        """)
        
        # Events table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                queue_name TEXT,
                worker_id TEXT,
                schedule_id TEXT,
                message TEXT,
                data TEXT,
                execution_time REAL,
                retry_count INTEGER,
                error TEXT,
                source TEXT DEFAULT 'omniq',
                level TEXT DEFAULT 'info',
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_queue_status ON tasks(queue_name, status)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_run_at ON tasks(run_at)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_tasks_expires_at ON tasks(expires_at)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run_at)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_schedules_status ON schedules(status)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_results_expires_at ON results(expires_at)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id)")
        await self._connection.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        
        await self._connection.commit()
    
    async def close_async(self):
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @asynccontextmanager
    async def get_connection_async(self):
        """Get a database connection with proper locking."""
        async with self._lock:
            if not self._connection:
                await self.initialize_async()
            yield self._connection
    
    def get_task_queue(self, queues: List[str] = None):
        """Get a SQLite task queue instance."""
        return SQLiteTaskQueue(self, queues or ["default"])
    
    def get_result_storage(self):
        """Get a SQLite result storage instance."""
        return SQLiteResultStorage(self)
    
    def get_event_storage(self):
        """Get a SQLite event storage instance."""
        return SQLiteEventStorage(self)
    
    # Sync wrappers
    def initialize(self):
        """Initialize the database synchronously."""
        return self._run_async(self.initialize_async())
    
    def close(self):
        """Close the database connection synchronously."""
        return self._run_async(self.close_async())
    
    @contextmanager
    def get_connection(self):
        """Get a database connection synchronously."""
        conn = self._run_async(self.get_connection_async().__aenter__())
        try:
            yield conn
        finally:
            self._run_async(self.get_connection_async().__aexit__(None, None, None))
    
    def _run_async(self, coro):
        """Run async coroutine in sync context using anyio."""
        import anyio
        return anyio.from_thread.run(coro)
```

### 2.2 SQLite Task Queue (`src/omniq/storage/sqlite_queue.py`)

**Purpose**: Implement a SQLite-based task queue with support for multiple named queues.

**Implementation Requirements**:
- Implement all abstract methods from BaseTaskQueue
- Support task enqueue/dequeue with priority ordering
- Implement task scheduling with pause/resume
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/storage/sqlite_queue.py
import json
import datetime as dt
from typing import List, Optional, Dict, Any
import aiosqlite

from ..base.queue import BaseTaskQueue
from ..models.task import Task, TaskStatus
from ..models.schedule import Schedule, ScheduleType, ScheduleStatus
from ..serialization.manager import SerializationManager

class SQLiteTaskQueue(BaseTaskQueue):
    """SQLite-based task queue implementation."""
    
    def __init__(self, backend: 'SQLiteBackend', queues: List[str] = None):
        super().__init__(backend.project_name, queues)
        self.backend = backend
        self.serialization_manager = SerializationManager()
    
    async def start_async(self):
        """Start the task queue."""
        # Ensure backend is initialized
        if not self.backend._connection:
            await self.backend.initialize_async()
    
    async def stop_async(self):
        """Stop the task queue."""
        # Nothing to do for SQLite
        pass
    
    async def enqueue_async(self, task: Task) -> str:
        """Enqueue a task."""
        async with self.backend.get_connection_async() as conn:
            # Serialize function if it's not already a string
            func_str = task.func
            if not isinstance(func_str, str):
                func_bytes = self.serialization_manager.serialize(func_str)
                func_str = func_bytes.decode('utf-8')
            
            # Insert task
            await conn.execute("""
                INSERT INTO tasks (
                    id, queue_name, status, func, func_args, func_kwargs,
                    name, description, tags, priority, run_at, created_at,
                    started_at, completed_at, ttl, expires_at, depends_on,
                    callback, callback_args, retry_count, max_retries,
                    retry_delay, result_ttl, store_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.queue_name, task.status.value, func_str,
                json.dumps(task.func_args), json.dumps(task.func_kwargs),
                task.name, task.description, json.dumps(task.tags),
                task.priority, task.run_at.isoformat() if task.run_at else None,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.ttl.total_seconds() if task.ttl else None,
                task.expires_at.isoformat() if task.expires_at else None,
                json.dumps(task.depends_on),
                task.callback if isinstance(task.callback, str) else None,
                json.dumps(task.callback_args),
                task.retry_count, task.max_retries,
                task.retry_delay.total_seconds() if task.retry_delay else None,
                task.result_ttl.total_seconds() if task.result_ttl else None,
                task.store_result
            ))
            
            await conn.commit()
            return task.id
    
    async def dequeue_async(self, queues: List[str] = None, timeout: float = None) -> Optional[Task]:
        """Dequeue a task."""
        queues = queues or self.queues
        
        async with self.backend.get_connection_async() as conn:
            # Build queue placeholders
            queue_placeholders = ','.join(['?' for _ in queues])
            
            # Get the next ready task
            cursor = await conn.execute(f"""
                SELECT * FROM tasks
                WHERE queue_name IN ({queue_placeholders})
                AND status = ?
                AND (run_at IS NULL OR run_at <= ?)
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """, (*queues, TaskStatus.PENDING.value, dt.datetime.utcnow().isoformat(), dt.datetime.utcnow().isoformat()))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Update task status to running
            await conn.execute("""
                UPDATE tasks SET status = ?, started_at = ?
                WHERE id = ?
            """, (TaskStatus.RUNNING.value, dt.datetime.utcnow().isoformat(), row[0]))
            
            await conn.commit()
            
            # Convert row to Task object
            return self._row_to_task(row)
    
    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_task(row)
    
    async def update_task_async(self, task: Task) -> bool:
        """Update a task."""
        async with self.backend.get_connection_async() as conn:
            # Check if task exists
            cursor = await conn.execute("SELECT id FROM tasks WHERE id = ?", (task.id,))
            if not await cursor.fetchone():
                return False
            
            # Serialize function if it's not already a string
            func_str = task.func
            if not isinstance(func_str, str):
                func_bytes = self.serialization_manager.serialize(func_str)
                func_str = func_bytes.decode('utf-8')
            
            # Update task
            await conn.execute("""
                UPDATE tasks SET
                    queue_name = ?, status = ?, func = ?, func_args = ?, func_kwargs = ?,
                    name = ?, description = ?, tags = ?, priority = ?, run_at = ?,
                    started_at = ?, completed_at = ?, ttl = ?, expires_at = ?,
                    depends_on = ?, callback = ?, callback_args = ?,
                    retry_count = ?, max_retries = ?, retry_delay = ?,
                    result_ttl = ?, store_result = ?
                WHERE id = ?
            """, (
                task.queue_name, task.status.value, func_str,
                json.dumps(task.func_args), json.dumps(task.func_kwargs),
                task.name, task.description, json.dumps(task.tags),
                task.priority, task.run_at.isoformat() if task.run_at else None,
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.ttl.total_seconds() if task.ttl else None,
                task.expires_at.isoformat() if task.expires_at else None,
                json.dumps(task.depends_on),
                task.callback if isinstance(task.callback, str) else None,
                json.dumps(task.callback_args),
                task.retry_count, task.max_retries,
                task.retry_delay.total_seconds() if task.retry_delay else None,
                task.result_ttl.total_seconds() if task.result_ttl else None,
                task.store_result, task.id
            ))
            
            await conn.commit()
            return True
    
    async def delete_task_async(self, task_id: str) -> bool:
        """Delete a task."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await conn.commit()
            return cursor.rowcount > 0
    
    async def size_async(self, queue_name: str = None) -> int:
        """Get queue size."""
        async with self.backend.get_connection_async() as conn:
            if queue_name:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE queue_name = ? AND status = ?",
                    (queue_name, TaskStatus.PENDING.value)
                )
            else:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = ?",
                    (TaskStatus.PENDING.value,)
                )
            
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def clear_async(self, queue_name: str = None) -> int:
        """Clear queue."""
        async with self.backend.get_connection_async() as conn:
            if queue_name:
                cursor = await conn.execute(
                    "DELETE FROM tasks WHERE queue_name = ? AND status = ?",
                    (queue_name, TaskStatus.PENDING.value)
                )
            else:
                cursor = await conn.execute(
                    "DELETE FROM tasks WHERE status = ?",
                    (TaskStatus.PENDING.value,)
                )
            
            await conn.commit()
            return cursor.rowcount
    
    async def schedule_async(self, schedule: Schedule) -> str:
        """Schedule a task."""
        async with self.backend.get_connection_async() as conn:
            # Insert schedule
            await conn.execute("""
                INSERT INTO schedules (
                    id, task_id, schedule_type, cron_expression, interval,
                    run_at, max_runs, status, created_at, last_run_at,
                    next_run_at, run_count, paused_at, resumed_at,
                    name, description, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule.id, schedule.task_id, schedule.schedule_type.value,
                schedule.cron_expression,
                schedule.interval.total_seconds() if schedule.interval else None,
                schedule.run_at.isoformat() if schedule.run_at else None,
                schedule.max_runs, schedule.status.value,
                schedule.created_at.isoformat(),
                schedule.last_run_at.isoformat() if schedule.last_run_at else None,
                schedule.next_run_at.isoformat() if schedule.next_run_at else None,
                schedule.run_count,
                schedule.paused_at.isoformat() if schedule.paused_at else None,
                schedule.resumed_at.isoformat() if schedule.resumed_at else None,
                schedule.name, schedule.description, json.dumps(schedule.tags)
            ))
            
            await conn.commit()
            return schedule.id
    
    async def get_schedule_async(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_schedule(row)
    
    async def update_schedule_async(self, schedule: Schedule) -> bool:
        """Update a schedule."""
        async with self.backend.get_connection_async() as conn:
            # Check if schedule exists
            cursor = await conn.execute("SELECT id FROM schedules WHERE id = ?", (schedule.id,))
            if not await cursor.fetchone():
                return False
            
            # Update schedule
            await conn.execute("""
                UPDATE schedules SET
                    task_id = ?, schedule_type = ?, cron_expression = ?,
                    interval = ?, run_at = ?, max_runs = ?, status = ?,
                    last_run_at = ?, next_run_at = ?, run_count = ?,
                    paused_at = ?, resumed_at = ?, name = ?,
                    description = ?, tags = ?
                WHERE id = ?
            """, (
                schedule.task_id, schedule.schedule_type.value,
                schedule.cron_expression,
                schedule.interval.total_seconds() if schedule.interval else None,
                schedule.run_at.isoformat() if schedule.run_at else None,
                schedule.max_runs, schedule.status.value,
                schedule.last_run_at.isoformat() if schedule.last_run_at else None,
                schedule.next_run_at.isoformat() if schedule.next_run_at else None,
                schedule.run_count,
                schedule.paused_at.isoformat() if schedule.paused_at else None,
                schedule.resumed_at.isoformat() if schedule.resumed_at else None,
                schedule.name, schedule.description, json.dumps(schedule.tags),
                schedule.id
            ))
            
            await conn.commit()
            return True
    
    async def delete_schedule_async(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            await conn.commit()
            return cursor.rowcount > 0
    
    async def get_ready_schedules_async(self) -> List[Schedule]:
        """Get ready-to-run schedules."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("""
                SELECT * FROM schedules
                WHERE status = ? AND next_run_at <= ?
                ORDER BY next_run_at ASC
            """, (ScheduleStatus.ACTIVE.value, dt.datetime.utcnow().isoformat()))
            
            rows = await cursor.fetchall()
            return [self._row_to_schedule(row) for row in rows]
    
    def _row_to_task(self, row) -> Task:
        """Convert a database row to a Task object."""
        return Task(
            id=row[0],
            func=row[3],
            func_args=json.loads(row[4]) if row[4] else {},
            func_kwargs=json.loads(row[5]) if row[5] else {},
            name=row[6],
            description=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            priority=row[9],
            run_at=dt.datetime.fromisoformat(row[10]) if row[10] else None,
            created_at=dt.datetime.fromisoformat(row[11]),
            started_at=dt.datetime.fromisoformat(row[12]) if row[12] else None,
            completed_at=dt.datetime.fromisoformat(row[13]) if row[13] else None,
            ttl=dt.timedelta(seconds=row[14]) if row[14] else None,
            expires_at=dt.datetime.fromisoformat(row[15]) if row[15] else None,
            depends_on=json.loads(row[16]) if row[16] else [],
            callback=row[17],
            callback_args=json.loads(row[18]) if row[18] else {},
            retry_count=row[19],
            max_retries=row[20],
            retry_delay=dt.timedelta(seconds=row[21]) if row[21] else None,
            result_ttl=dt.timedelta(seconds=row[22]) if row[22] else None,
            store_result=bool(row[23]),
            queue_name=row[1],
            status=TaskStatus(row[2])
        )
    
    def _row_to_schedule(self, row) -> Schedule:
        """Convert a database row to a Schedule object."""
        return Schedule(
            id=row[0],
            task_id=row[1],
            schedule_type=ScheduleType(row[2]),
            cron_expression=row[3],
            interval=dt.timedelta(seconds=row[4]) if row[4] else None,
            run_at=dt.datetime.fromisoformat(row[5]) if row[5] else None,
            max_runs=row[6],
            status=ScheduleStatus(row[7]),
            created_at=dt.datetime.fromisoformat(row[8]),
            last_run_at=dt.datetime.fromisoformat(row[9]) if row[9] else None,
            next_run_at=dt.datetime.fromisoformat(row[10]) if row[10] else None,
            run_count=row[11],
            paused_at=dt.datetime.fromisoformat(row[12]) if row[12] else None,
            resumed_at=dt.datetime.fromisoformat(row[13]) if row[13] else None,
            name=row[14],
            description=row[15],
            tags=json.loads(row[16]) if row[16] else []
        )
```

### 2.3 SQLite Result Storage (`src/omniq/storage/sqlite_result.py`)

**Purpose**: Implement a SQLite-based result storage with TTL support.

**Implementation Requirements**:
- Implement all abstract methods from BaseResultStorage
- Support result storage and retrieval
- Implement TTL-based cleanup
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/storage/sqlite_result.py
import json
import datetime as dt
from typing import Optional, Dict, Any, List
import aiosqlite

from ..base.result_storage import BaseResultStorage
from ..models.result import TaskResult, ResultStatus

class SQLiteResultStorage(BaseResultStorage):
    """SQLite-based result storage implementation."""
    
    def __init__(self, backend: 'SQLiteBackend'):
        super().__init__(backend.project_name)
        self.backend = backend
    
    async def start_async(self):
        """Start the result storage."""
        # Ensure backend is initialized
        if not self.backend._connection:
            await self.backend.initialize_async()
    
    async def stop_async(self):
        """Stop the result storage."""
        # Nothing to do for SQLite
        pass
    
    async def store_async(self, result: TaskResult) -> bool:
        """Store a result."""
        async with self.backend.get_connection_async() as conn:
            # Serialize result data
            result_data = json.dumps(result.result) if result.result is not None else None
            
            # Insert or replace result
            await conn.execute("""
                INSERT OR REPLACE INTO results (
                    task_id, status, result, error, error_traceback,
                    created_at, started_at, completed_at, ttl, expires_at,
                    execution_time, worker_id, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.task_id, result.status.value, result_data,
                result.error, result.error_traceback,
                result.created_at.isoformat(),
                result.started_at.isoformat() if result.started_at else None,
                result.completed_at.isoformat() if result.completed_at else None,
                result.ttl.total_seconds() if result.ttl else None,
                result.expires_at.isoformat() if result.expires_at else None,
                result.execution_time, result.worker_id, result.retry_count
            ))
            
            await conn.commit()
            return True
    
    async def get_async(self, task_id: str) -> Optional[TaskResult]:
        """Get a result by task ID."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("SELECT * FROM results WHERE task_id = ?", (task_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            
            return self._row_to_result(row)
    
    async def get_latest_async(self, schedule_id: str) -> Optional[TaskResult]:
        """Get the latest result for a schedule."""
        async with self.backend.get_connection_async() as conn:
            # Get the latest task ID for this schedule
            cursor = await conn.execute("""
                SELECT t.id FROM tasks t
                JOIN schedules s ON t.id = s.task_id
                WHERE s.id = ?
                ORDER BY t.created_at DESC
                LIMIT 1
            """, (schedule_id,))
            
            task_row = await cursor.fetchone()
            if not task_row:
                return None
            
            task_id = task_row[0]
            
            # Get the result for this task
            return await self.get_async(task_id)
    
    async def update_async(self, result: TaskResult) -> bool:
        """Update a result."""
        # For SQLite, update is the same as store
        return await self.store_async(result)
    
    async def delete_async(self, task_id: str) -> bool:
        """Delete a result."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute("DELETE FROM results WHERE task_id = ?", (task_id,))
            await conn.commit()
            return cursor.rowcount > 0
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired results."""
        async with self.backend.get_connection_async() as conn:
            cursor = await conn.execute(
                "DELETE FROM results WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (dt.datetime.utcnow().isoformat(),)
            )
            await conn.commit()
            return cursor.rowcount
    
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get storage statistics."""
        async with self.backend.get_connection_async() as conn:
            stats = {}
            
            # Total results
            cursor = await conn.execute("SELECT COUNT(*) FROM results")
            stats["total"] = (await cursor.fetchone())[0]
            
            # Results by status
            for status in ResultStatus:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM results WHERE status = ?",
                    (status.value,)
                )
                stats[f"status_{status.value}"] = (await cursor.fetchone())[0]
            
            # Expired results
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM results WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (dt.datetime.utcnow().isoformat(),)
            )
            stats["expired"] = (await cursor.fetchone())[0]
            
            return stats
    
    def _row_to_result(self, row) -> TaskResult:
        """Convert a database row to a TaskResult object."""
        return TaskResult(
            task_id=row[0],
            status=ResultStatus(row[1]),
            result=json.loads(row[2]) if row[2] else None,
            error=row[3],
            error_traceback=row[4],
            created_at=dt.datetime.fromisoformat(row[5]),
            started_at=dt.datetime.fromisoformat(row[6]) if row[6] else None,
            completed_at=dt.datetime.fromisoformat(row[7]) if row[7] else None,
            ttl=dt.timedelta(seconds=row[8]) if row[8] else None,
            expires_at=dt.datetime.fromisoformat(row[9]) if row[9] else None,
            execution_time=row[10],
            worker_id=row[11],
            retry_count=row[12]
        )
```

### 2.4 SQLite Event Storage (`src/omniq/storage/sqlite_event.py`)

**Purpose**: Implement a SQLite-based event storage with structured querying.

**Implementation Requirements**:
- Implement all abstract methods from BaseEventStorage
- Support event logging and retrieval
- Implement filtering by various criteria
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/storage/sqlite_event.py
import json
import datetime as dt
from typing import List, Optional, Dict, Any
import aiosqlite

from ..base.event_storage import BaseEventStorage
from ..models.event import TaskEvent, EventType

class SQLiteEventStorage(BaseEventStorage):
    """SQLite-based event storage implementation."""
    
    def __init__(self, backend: 'SQLiteBackend'):
        super().__init__(backend.project_name)
        self.backend = backend
    
    async def start_async(self):
        """Start the event storage."""
        # Ensure backend is initialized
        if not self.backend._connection:
            await self.backend.initialize_async()
    
    async def stop_async(self):
        """Stop the event storage."""
        # Nothing to do for SQLite
        pass
    
    async def log_async(self, event: TaskEvent) -> bool:
        """Log an event."""
        async with self.backend.get_connection_async() as conn:
            # Insert event
            await conn.execute("""
                INSERT INTO events (
                    id, task_id, event_type, timestamp, queue_name,
                    worker_id, schedule_id, message, data, execution_time,
                    retry_count, error, source, level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.id, event.task_id, event.event_type.value,
                event.timestamp.isoformat(), event.queue_name,
                event.worker_id, event.schedule_id, event.message,
                json.dumps(event.data), event.execution_time,
                event.retry_count, event.error, event.source, event.level
            ))
            
            await conn.commit()
            return True
    
    async def get_events_async(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[dt.datetime] = None,
        end_time: Optional[dt.datetime] = None,
        limit: int = 100
    ) -> List[TaskEvent]:
        """Get events."""
        async with self.backend.get_connection_async() as conn:
            # Build query conditions
            conditions = []
            params = []
            
            if task_id:
                conditions.append("task_id = ?")
                params.append(task_id)
            
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type.value)
            
            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time.isoformat())
            
            # Build WHERE clause
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            # Execute query
            query = f"""
                SELECT * FROM events
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            return [self._row_to_event(row) for row in rows]
    
    async def get_latest_events_async(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 10
    ) -> List[TaskEvent]:
        """Get latest events."""
        async with self.backend.get_connection_async() as conn:
            # Build query conditions
            conditions = []
            params = []
            
            if task_id:
                conditions.append("task_id = ?")
                params.append(task_id)
            
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type.value)
            
            # Build WHERE clause
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            # Execute query
            query = f"""
                SELECT * FROM events
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            
            return [self._row_to_event(row) for row in rows]
    
    async def cleanup_expired_async(self) -> int:
        """Clean up expired events."""
        # For events, we'll keep all events for now
        # In a real implementation, you might want to implement
        # a retention policy based on event age or count
        return 0
    
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get storage statistics."""
        async with self.backend.get_connection_async() as conn:
            stats = {}
            
            # Total events
            cursor = await conn.execute("SELECT COUNT(*) FROM events")
            stats["total"] = (await cursor.fetchone())[0]
            
            # Events by type
            for event_type in EventType:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM events WHERE event_type = ?",
                    (event_type.value,)
                )
                stats[f"type_{event_type.value}"] = (await cursor.fetchone())[0]
            
            # Events by level
            for level in ["debug", "info", "warning", "error"]:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM events WHERE level = ?",
                    (level,)
                )
                stats[f"level_{level}"] = (await cursor.fetchone())[0]
            
            return stats
    
    def _row_to_event(self, row) -> TaskEvent:
        """Convert a database row to a TaskEvent object."""
        return TaskEvent(
            id=row[0],
            task_id=row[1],
            event_type=EventType(row[2]),
            timestamp=dt.datetime.fromisoformat(row[3]),
            queue_name=row[4],
            worker_id=row[5],
            schedule_id=row[6],
            message=row[7],
            data=json.loads(row[8]) if row[8] else {},
            execution_time=row[9],
            retry_count=row[10],
            error=row[11],
            source=row[12],
            level=row[13]
        )
```

### 2.5 SQLite Worker (`src/omniq/workers/sqlite_worker.py`)

**Purpose**: Implement a worker that works with SQLite backend components.

**Implementation Requirements**:
- Implement all abstract methods from BaseWorker
- Support task processing with proper error handling
- Implement event logging for task lifecycle
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/workers/sqlite_worker.py
import asyncio
import datetime as dt
from typing import Optional, Dict, Any, List, Callable
import anyio

from ..base.worker import BaseWorker
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent, EventType

class SQLiteWorker(BaseWorker):
    """Worker implementation for SQLite backend."""
    
    def __init__(
        self,
        task_queue,
        result_storage,
        event_storage,
        worker_id: Optional[str] = None,
        max_workers: int = 1,
        poll_interval: float = 1.0,
        **kwargs
    ):
        super().__init__(task_queue, result_storage, event_storage, worker_id, **kwargs)
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._stop_event = asyncio.Event()
    
    async def start_async(self):
        """Start the worker."""
        self.is_running = True
        self._stop_event.clear()
        
        # Start the main worker loop
        asyncio.create_task(self._worker_loop())
    
    async def stop_async(self):
        """Stop the worker."""
        self.is_running = False
        self._stop_event.set()
        
        # Wait for running tasks to complete
        if self._running_tasks:
            await asyncio.gather(*self._running_tasks.values(), return_exceptions=True)
            self._running_tasks.clear()
    
    async def process_task_async(self, task: Task) -> TaskResult:
        """Process a task."""
        return await self._execute_task_async(task)
    
    async def get_stats_async(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "worker_id": self.worker_id,
            "is_running": self.is_running,
            "max_workers": self.max_workers,
            "running_tasks": len(self._running_tasks),
            "completed_tasks": getattr(self, "_completed_count", 0),
            "failed_tasks": getattr(self, "_failed_count", 0)
        }
    
    async def _worker_loop(self):
        """Main worker loop."""
        while self.is_running:
            try:
                # Check if we have capacity for more tasks
                if len(self._running_tasks) < self.max_workers:
                    # Get a task from the queue
                    task = await self.task_queue.dequeue_async(
                        queues=self.task_queue.queues,
                        timeout=0.1  # Short timeout to allow checking stop event
                    )
                    
                    if task:
                        # Process the task
                        task_coro = self._process_task_with_tracking(task)
                        task_task = asyncio.create_task(task_coro)
                        self._running_tasks[task.id] = task_task
                        
                        # Set up callback to remove task when done
                        task_task.add_done_callback(
                            lambda t, task_id=task.id: self._running_tasks.pop(task_id, None)
                        )
                
                # Process ready schedules
                await self._process_schedules()
                
                # Clean up completed tasks
                self._cleanup_completed_tasks()
                
                # Wait for next poll or stop event
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval
                    )
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                # Log error but continue running
                try:
                    event = TaskEvent(
                        task_id="worker",
                        event_type=EventType.ERROR,
                        message=f"Worker error: {str(e)}",
                        error=str(e),
                        level="error"
                    )
                    await self.event_storage.log_async(event)
                except Exception:
                    pass  # Avoid infinite recursion
    
    async def _process_task_with_tracking(self, task: Task):
        """Process a task with error tracking."""
        try:
            result = await self._execute_task_async(task)
            
            # Update success counter
            self._completed_count = getattr(self, "_completed_count", 0) + 1
            
            return result
        except Exception as e:
            # Update failure counter
            self._failed_count = getattr(self, "_failed_count", 0) + 1
            
            # Re-raise the exception
            raise
    
    async def _process_schedules(self):
        """Process ready schedules."""
        # Get ready schedules
        schedules = await self.task_queue.get_ready_schedules_async()
        
        for schedule in schedules:
            try:
                # Get the task for this schedule
                task = await self.task_queue.get_task_async(schedule.task_id)
                if not task:
                    continue
                
                # Create a new task based on the scheduled task
                new_task = Task(
                    id=str(task.id),  # Use same ID to overwrite
                    func=task.func,
                    func_args=task.func_args,
                    func_kwargs=task.func_kwargs,
                    queue_name=task.queue_name,
                    ttl=task.ttl,
                    result_ttl=task.result_ttl,
                    name=task.name,
                    description=task.description,
                    tags=task.tags,
                    priority=task.priority,
                    depends_on=task.depends_on,
                    callback=task.callback,
                    callback_args=task.callback_args,
                    max_retries=task.max_retries,
                    retry_delay=task.retry_delay,
                    store_result=task.store_result
                )
                
                # Enqueue the new task
                await self.task_queue.enqueue_async(new_task)
                
                # Update the schedule
                schedule.mark_run()
                await self.task_queue.update_schedule_async(schedule)
                
            except Exception as e:
                # Log error but continue processing other schedules
                try:
                    event = TaskEvent(
                        task_id=schedule.task_id,
                        event_type=EventType.ERROR,
                        message=f"Schedule processing error: {str(e)}",
                        error=str(e),
                        level="error"
                    )
                    await self.event_storage.log_async(event)
                except Exception:
                    pass  # Avoid infinite recursion
    
    def _cleanup_completed_tasks(self):
        """Clean up completed tasks."""
        # Remove completed tasks from the running tasks dict
        completed_tasks = [
            task_id for task_id, task in self._running_tasks.items()
            if task.done()
        ]
        
        for task_id in completed_tasks:
            self._running_tasks.pop(task_id, None)
```

### 2.6 Backend Factory (`src/omniq/backends/factory.py`)

**Purpose**: Create a factory for instantiating SQLite backend components.

**Implementation Requirements**:
- Provide functions to create backend components
- Support both direct instantiation and configuration-based creation
- Follow the "Async First, Sync Wrapped" pattern

**Code Structure**:
```python
# src/omniq/backends/factory.py
from typing import List, Optional, Dict, Any, Union

from .sqlite import SQLiteBackend
from ..storage.sqlite_queue import SQLiteTaskQueue
from ..storage.sqlite_result import SQLiteResultStorage
from ..storage.sqlite_event import SQLiteEventStorage
from ..workers.sqlite_worker import SQLiteWorker
from ..models.config import OmniQConfig, TaskQueueConfig, ResultStorageConfig, EventStorageConfig, WorkerConfig

def create_sqlite_backend(
    project_name: str,
    base_dir: str = "./omniq_data",
    **kwargs
) -> SQLiteBackend:
    """Create a SQLite backend."""
    return SQLiteBackend(project_name=project_name, base_dir=base_dir, **kwargs)

def create_sqlite_task_queue(
    backend: SQLiteBackend,
    queues: List[str] = None
) -> SQLiteTaskQueue:
    """Create a SQLite task queue."""
    return backend.get_task_queue(queues)

def create_sqlite_result_storage(
    backend: SQLiteBackend
) -> SQLiteResultStorage:
    """Create a SQLite result storage."""
    return backend.get_result_storage()

def create_sqlite_event_storage(
    backend: SQLiteBackend
) -> SQLiteEventStorage:
    """Create a SQLite event storage."""
    return backend.get_event_storage()

def create_sqlite_worker(
    task_queue: SQLiteTaskQueue,
    result_storage: SQLiteResultStorage,
    event_storage: SQLiteEventStorage,
    worker_id: Optional[str] = None,
    max_workers: int = 1,
    poll_interval: float = 1.0,
    **kwargs
) -> SQLiteWorker:
    """Create a SQLite worker."""
    return SQLiteWorker(
        task_queue=task_queue,
        result_storage=result_storage,
        event_storage=event_storage,
        worker_id=worker_id,
        max_workers=max_workers,
        poll_interval=poll_interval,
        **kwargs
    )

def create_sqlite_components_from_config(
    config: Union[OmniQConfig, Dict[str, Any]]
) -> Dict[str, Any]:
    """Create SQLite components from configuration."""
    if isinstance(config, dict):
        config = OmniQConfig.from_dict(config)
    
    # Create backend
    backend = create_sqlite_backend(
        project_name=config.project_name,
        base_dir=config.task_queue.base_dir or f"./{config.project_name}_data"
    )
    
    # Create components
    task_queue = create_sqlite_task_queue(
        backend=backend,
        queues=config.task_queue.queues
    )
    
    result_storage = create_sqlite_result_storage(backend=backend)
    
    event_storage = create_sqlite_event_storage(backend=backend)
    
    worker = create_sqlite_worker(
        task_queue=task_queue,
        result_storage=result_storage,
        event_storage=event_storage,
        max_workers=config.worker.max_workers
    )
    
    return {
        "backend": backend,
        "task_queue": task_queue,
        "result_storage": result_storage,
        "event_storage": event_storage,
        "worker": worker
    }

# Convenience functions for direct import
def get_task_queue(backend: SQLiteBackend, queues: List[str] = None) -> SQLiteTaskQueue:
    """Get a task queue from a backend."""
    return create_sqlite_task_queue(backend, queues)

def get_result_storage(backend: SQLiteBackend) -> SQLiteResultStorage:
    """Get a result storage from a backend."""
    return create_sqlite_result_storage(backend)

def get_event_storage(backend: SQLiteBackend) -> SQLiteEventStorage:
    """Get an event storage from a backend."""
    return create_sqlite_event_storage(backend)

def get_worker(
    worker_type: str,
    task_queue: SQLiteTaskQueue,
    result_storage: SQLiteResultStorage,
    event_storage: SQLiteEventStorage,
    **kwargs
) -> SQLiteWorker:
    """Get a worker for the SQLite backend."""
    if worker_type == "async":
        return create_sqlite_worker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported worker type for SQLite backend: {worker_type}")
```

## Implementation Notes

### Async First, Sync Wrapped Implementation

The SQLite backend implementation follows the "Async First, Sync Wrapped" pattern:

1. **Async Operations**: All database operations use aiosqlite for async access
2. **Connection Management**: Proper connection handling with async context managers
3. **Sync Wrappers**: Synchronous methods provided by base classes
4. **Error Handling**: Consistent error handling across all components

### Database Schema Design

The database schema is designed for:

1. **Performance**: Indexes on frequently queried columns
2. **Relationships**: Foreign key constraints for data integrity
3. **Flexibility**: JSON columns for complex data structures
4. **Maintenance**: TTL columns for automatic cleanup

### Worker Implementation

The SQLite worker implementation includes:

1. **Concurrent Processing**: Support for multiple concurrent tasks
2. **Schedule Processing**: Automatic processing of ready schedules
3. **Error Handling**: Robust error handling and logging
4. **Resource Management**: Proper cleanup of completed tasks

## Testing Strategy

For Task 2, the following tests should be implemented:

1. **Backend Tests**: Verify backend initialization and connection management
2. **Task Queue Tests**: Test task enqueue/dequeue with various scenarios
3. **Result Storage Tests**: Verify result storage and retrieval
4. **Event Storage Tests**: Test event logging and querying
5. **Worker Tests**: Test task processing and schedule handling
6. **Integration Tests**: Test end-to-end workflows

## Dependencies

Task 2 requires the following dependencies:

- Core: `aiosqlite` (in addition to Task 1 dependencies)
- Development: Same as Task 1

## Deliverables

1. Complete SQLite backend implementation with task queue, result storage, and event storage
2. SQLite worker implementation with concurrent processing
3. Backend factory for easy component creation
4. Comprehensive test suite for all SQLite components
5. Documentation for all SQLite-specific APIs