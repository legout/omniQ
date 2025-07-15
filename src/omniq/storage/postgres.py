"""
PostgreSQL storage implementation for OmniQ.

This module provides PostgreSQL-based implementations for task queue,
result storage, event storage, and schedule storage using asyncpg.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import asyncpg
import msgspec

from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage, BaseScheduleStorage
from ..models.task import Task, TaskStatus
from ..models.result import TaskResult, ResultStatus
from ..models.event import TaskEvent
from ..models.schedule import Schedule, ScheduleStatus


class AsyncPostgresQueue(BaseTaskQueue):
    """
    Async PostgreSQL-based task queue implementation.
    
    This class implements the BaseTaskQueue interface using PostgreSQL
    for persistent task storage with support for multiple queues,
    priority ordering, and row-level locking.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "omniq",
        username: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
        command_timeout: float = 60.0,
        schema: str = "public",
        tasks_table: str = "tasks",
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self.schema = schema
        self.tasks_table = tasks_table
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        if self._pool is not None:
            return
        
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password,
            min_size=self.min_connections,
            max_size=self.max_connections,
            command_timeout=self.command_timeout,
        )
        
        # Create schema if it doesn't exist
        async with self._pool.acquire() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            
            # Create tasks table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{self.tasks_table} (
                    id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    func TEXT NOT NULL,
                    args JSONB NOT NULL,
                    kwargs JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    run_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    retry_delay REAL NOT NULL DEFAULT 1.0,
                    dependencies JSONB NOT NULL DEFAULT '[]',
                    callbacks JSONB NOT NULL DEFAULT '{{}}',
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    task_data JSONB NOT NULL
                )
            """)
            
            # Create indexes for performance
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_queue_priority 
                ON {self.schema}.{self.tasks_table}(queue_name, priority DESC, created_at ASC)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_status 
                ON {self.schema}.{self.tasks_table}(status)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_run_at 
                ON {self.schema}.{self.tasks_table}(run_at)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_expires_at 
                ON {self.schema}.{self.tasks_table}(expires_at)
            """)
    
    async def disconnect(self) -> None:
        """Disconnect from the PostgreSQL database."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    def _serialize_task(self, task: Task) -> Dict[str, Any]:
        """Serialize a task for database storage."""
        return {
            "id": task.id,
            "queue_name": task.queue_name,
            "priority": task.priority,
            "status": task.status.value,
            "func": str(task.func),
            "args": json.dumps(task.args),
            "kwargs": json.dumps(task.kwargs),
            "created_at": task.created_at,
            "run_at": task.run_at,
            "expires_at": task.expires_at,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "retry_delay": task.retry_delay.total_seconds(),
            "dependencies": json.dumps(task.dependencies),
            "callbacks": json.dumps({k: str(v) for k, v in task.callbacks.items()}),
            "metadata": json.dumps(task.metadata),
            "task_data": msgspec.json.encode(task).decode()
        }
    
    def _deserialize_task(self, row: Dict[str, Any]) -> Task:
        """Deserialize a task from database storage."""
        # Use the stored msgspec data for accurate deserialization
        return msgspec.json.decode(row["task_data"], type=Task)
    
    async def enqueue(self, task: Task) -> str:
        """Enqueue a task for processing."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        task_data = self._serialize_task(task)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.schema}.{self.tasks_table} (
                    id, queue_name, priority, status, func, args, kwargs,
                    created_at, run_at, expires_at, retry_count, max_retries,
                    retry_delay, dependencies, callbacks, metadata, task_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """, 
                task_data["id"], task_data["queue_name"], task_data["priority"],
                task_data["status"], task_data["func"], task_data["args"],
                task_data["kwargs"], task_data["created_at"], task_data["run_at"],
                task_data["expires_at"], task_data["retry_count"], task_data["max_retries"],
                task_data["retry_delay"], task_data["dependencies"], task_data["callbacks"],
                task_data["metadata"], task_data["task_data"]
            )
        
        return task.id
    
    async def dequeue(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task from the specified queues."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        # Build query for multiple queues with priority ordering
        queue_placeholders = ",".join(f"${i+1}" for i in range(len(queues)))
        now = datetime.utcnow()
        
        query = f"""
            UPDATE {self.schema}.{self.tasks_table}
            SET status = 'running'
            WHERE id = (
                SELECT id FROM {self.schema}.{self.tasks_table}
                WHERE queue_name = ANY($1::text[])
                AND status = 'pending'
                AND (run_at IS NULL OR run_at <= $2)
                AND (expires_at IS NULL OR expires_at > $2)
                ORDER BY priority DESC, created_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, queues, now)
            
            if row is None:
                return None
            
            # Convert row to dict
            task_dict = dict(row)
            return self._deserialize_task(task_dict)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self.schema}.{self.tasks_table} WHERE id = $1",
                task_id
            )
            
            if row is None:
                return None
            
            task_dict = dict(row)
            return self._deserialize_task(task_dict)
    
    async def update_task(self, task: Task) -> None:
        """Update a task in the queue."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        task_data = self._serialize_task(task)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {self.schema}.{self.tasks_table} SET
                    queue_name = $2, priority = $3, status = $4, func = $5,
                    args = $6, kwargs = $7, run_at = $8, expires_at = $9,
                    retry_count = $10, max_retries = $11, retry_delay = $12,
                    dependencies = $13, callbacks = $14, metadata = $15, task_data = $16
                WHERE id = $1
            """,
                task.id, task_data["queue_name"], task_data["priority"], task_data["status"],
                task_data["func"], task_data["args"], task_data["kwargs"],
                task_data["run_at"], task_data["expires_at"], task_data["retry_count"],
                task_data["max_retries"], task_data["retry_delay"], task_data["dependencies"],
                task_data["callbacks"], task_data["metadata"], task_data["task_data"]
            )
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task from the queue."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.tasks_table} WHERE id = $1",
                task_id
            )
            
            return result.split()[-1] != "0"  # Check if any rows were affected
    
    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """List tasks in the queue."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        query = f"SELECT * FROM {self.schema}.{self.tasks_table} WHERE 1=1"
        params = []
        param_count = 0
        
        if queue_name is not None:
            param_count += 1
            query += f" AND queue_name = ${param_count}"
            params.append(queue_name)
        
        if status is not None:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)
        
        query += " ORDER BY priority DESC, created_at ASC"
        
        if limit is not None:
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
        
        if offset > 0:
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            tasks = []
            for row in rows:
                task_dict = dict(row)
                tasks.append(self._deserialize_task(task_dict))
            
            return tasks
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Get the number of tasks in a queue."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT COUNT(*) FROM {self.schema}.{self.tasks_table} WHERE queue_name = $1 AND status = 'pending'",
                queue_name
            )
            
            return row[0] if row else 0
    
    async def cleanup_expired_tasks(self) -> int:
        """Clean up expired tasks."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        now = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.tasks_table} WHERE expires_at IS NOT NULL AND expires_at <= $1",
                now
            )
            
            return int(result.split()[-1])  # Extract number of affected rows


class PostgresQueue(AsyncPostgresQueue):
    """
    Synchronous wrapper around AsyncPostgresQueue.
    
    This class provides a synchronous interface to the async PostgreSQL queue
    implementation using anyio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the PostgreSQL database (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from the PostgreSQL database (sync)."""
        asyncio.run(self.disconnect())
    
    def enqueue_sync(self, task: Task) -> str:
        """Enqueue a task for processing (sync)."""
        return asyncio.run(self.enqueue(task))
    
    def dequeue_sync(self, queues: List[str], timeout: Optional[float] = None) -> Optional[Task]:
        """Dequeue a task from the specified queues (sync)."""
        return asyncio.run(self.dequeue(queues, timeout))
    
    def get_task_sync(self, task_id: str) -> Optional[Task]:
        """Get a task by ID (sync)."""
        return asyncio.run(self.get_task(task_id))
    
    def update_task_sync(self, task: Task) -> None:
        """Update a task in the queue (sync)."""
        asyncio.run(self.update_task(task))
    
    def delete_task_sync(self, task_id: str) -> bool:
        """Delete a task from the queue (sync)."""
        return asyncio.run(self.delete_task(task_id))
    
    def list_tasks_sync(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Task]:
        """List tasks in the queue (sync)."""
        return asyncio.run(self.list_tasks(queue_name, status, limit, offset))
    
    def get_queue_size_sync(self, queue_name: str) -> int:
        """Get the number of tasks in a queue (sync)."""
        return asyncio.run(self.get_queue_size(queue_name))
    
    def cleanup_expired_tasks_sync(self) -> int:
        """Clean up expired tasks (sync)."""
        return asyncio.run(self.cleanup_expired_tasks())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncPostgresResultStorage(BaseResultStorage):
    """
    Async PostgreSQL-based result storage implementation.
    
    This class implements the BaseResultStorage interface using PostgreSQL
    for persistent result storage.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "omniq",
        username: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
        command_timeout: float = 60.0,
        schema: str = "public",
        results_table: str = "results",
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self.schema = schema
        self.results_table = results_table
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        if self._pool is not None:
            return
        
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password,
            min_size=self.min_connections,
            max_size=self.max_connections,
            command_timeout=self.command_timeout,
        )
        
        # Create schema if it doesn't exist
        async with self._pool.acquire() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            
            # Create results table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{self.results_table} (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result JSONB,
                    error TEXT,
                    error_type TEXT,
                    traceback TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ,
                    worker_id TEXT,
                    execution_time REAL,
                    memory_usage BIGINT,
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    result_data JSONB NOT NULL
                )
            """)
            
            # Create indexes for performance
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.results_table}_status
                ON {self.schema}.{self.results_table}(status)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.results_table}_expires_at
                ON {self.schema}.{self.results_table}(expires_at)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.results_table}_completed_at
                ON {self.schema}.{self.results_table}(completed_at)
            """)
    
    async def disconnect(self) -> None:
        """Disconnect from the PostgreSQL database."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    def _serialize_result(self, result: TaskResult) -> Dict[str, Any]:
        """Serialize a result for database storage."""
        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": json.dumps(result.result) if result.result is not None else None,
            "error": result.error,
            "error_type": result.error_type,
            "traceback": result.traceback,
            "created_at": result.created_at,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "expires_at": result.expires_at,
            "worker_id": result.worker_id,
            "execution_time": result.execution_time,
            "memory_usage": result.memory_usage,
            "metadata": json.dumps(result.metadata),
            "result_data": msgspec.json.encode(result).decode()
        }
    
    def _deserialize_result(self, row: Dict[str, Any]) -> TaskResult:
        """Deserialize a result from database storage."""
        # Use the stored msgspec data for accurate deserialization
        return msgspec.json.decode(row["result_data"], type=TaskResult)
    
    async def get(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self.schema}.{self.results_table} WHERE task_id = $1",
                task_id
            )
            
            if row is None:
                return None
            
            result_dict = dict(row)
            return self._deserialize_result(result_dict)
    
    async def set(self, result: TaskResult) -> None:
        """Store a task result."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        result_data = self._serialize_result(result)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.schema}.{self.results_table} (
                    task_id, status, result, error, error_type, traceback,
                    created_at, started_at, completed_at, expires_at,
                    worker_id, execution_time, memory_usage, metadata, result_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    result = EXCLUDED.result,
                    error = EXCLUDED.error,
                    error_type = EXCLUDED.error_type,
                    traceback = EXCLUDED.traceback,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at,
                    expires_at = EXCLUDED.expires_at,
                    worker_id = EXCLUDED.worker_id,
                    execution_time = EXCLUDED.execution_time,
                    memory_usage = EXCLUDED.memory_usage,
                    metadata = EXCLUDED.metadata,
                    result_data = EXCLUDED.result_data
            """,
                result_data["task_id"], result_data["status"], result_data["result"],
                result_data["error"], result_data["error_type"], result_data["traceback"],
                result_data["created_at"], result_data["started_at"], result_data["completed_at"],
                result_data["expires_at"], result_data["worker_id"], result_data["execution_time"],
                result_data["memory_usage"], result_data["metadata"], result_data["result_data"]
            )
    
    async def delete(self, task_id: str) -> bool:
        """Delete a task result."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.results_table} WHERE task_id = $1",
                task_id
            )
            
            return result.split()[-1] != "0"  # Check if any rows were affected
    
    async def list_results(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """List task results."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        query = f"SELECT * FROM {self.schema}.{self.results_table} WHERE 1=1"
        params = []
        param_count = 0
        
        if status is not None:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)
        
        query += " ORDER BY completed_at DESC"
        
        if limit is not None:
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
        
        if offset > 0:
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            results = []
            for row in rows:
                result_dict = dict(row)
                results.append(self._deserialize_result(result_dict))
            
            return results
    
    async def cleanup_expired_results(self) -> int:
        """Clean up expired results."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        now = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.results_table} WHERE expires_at IS NOT NULL AND expires_at <= $1",
                now
            )
            
            return int(result.split()[-1])  # Extract number of affected rows


class PostgresResultStorage(AsyncPostgresResultStorage):
    """
    Synchronous wrapper around AsyncPostgresResultStorage.
    
    This class provides a synchronous interface to the async PostgreSQL result storage
    implementation using anyio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the PostgreSQL database (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from the PostgreSQL database (sync)."""
        asyncio.run(self.disconnect())
    
    def get_sync(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID (sync)."""
        return asyncio.run(self.get(task_id))
    
    def set_sync(self, result: TaskResult) -> None:
        """Store a task result (sync)."""
        asyncio.run(self.set(result))
    
    def delete_sync(self, task_id: str) -> bool:
        """Delete a task result (sync)."""
        return asyncio.run(self.delete(task_id))
    
    def list_results_sync(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskResult]:
        """List task results (sync)."""
        return asyncio.run(self.list_results(status, limit, offset))
    
    def cleanup_expired_results_sync(self) -> int:
        """Clean up expired results (sync)."""
        return asyncio.run(self.cleanup_expired_results())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncPostgresEventStorage(BaseEventStorage):
    """
    Async PostgreSQL-based event storage implementation.
    
    This class implements the BaseEventStorage interface using PostgreSQL
    for persistent event logging.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "omniq",
        username: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
        command_timeout: float = 60.0,
        schema: str = "public",
        events_table: str = "events",
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self.schema = schema
        self.events_table = events_table
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        if self._pool is not None:
            return
        
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password,
            min_size=self.min_connections,
            max_size=self.max_connections,
            command_timeout=self.command_timeout,
        )
        
        # Create schema if it doesn't exist
        async with self._pool.acquire() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            
            # Create events table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{self.events_table} (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    message TEXT,
                    details JSONB NOT NULL DEFAULT '{{}}',
                    worker_id TEXT,
                    queue_name TEXT,
                    schedule_id TEXT,
                    error_type TEXT,
                    error_message TEXT,
                    traceback TEXT,
                    execution_time REAL,
                    memory_usage BIGINT,
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    event_data JSONB NOT NULL
                )
            """)
            
            # Create indexes for performance
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.events_table}_task_id
                ON {self.schema}.{self.events_table}(task_id)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.events_table}_event_type
                ON {self.schema}.{self.events_table}(event_type)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.events_table}_timestamp
                ON {self.schema}.{self.events_table}(timestamp)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.events_table}_worker_id
                ON {self.schema}.{self.events_table}(worker_id)
            """)
    
    async def disconnect(self) -> None:
        """Disconnect from the PostgreSQL database."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    def _serialize_event(self, event: TaskEvent) -> Dict[str, Any]:
        """Serialize an event for database storage."""
        return {
            "id": event.id,
            "task_id": event.task_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp,
            "message": event.message,
            "details": json.dumps(event.details),
            "worker_id": event.worker_id,
            "queue_name": event.queue_name,
            "schedule_id": event.schedule_id,
            "error_type": event.error_type,
            "error_message": event.error_message,
            "traceback": event.traceback,
            "execution_time": event.execution_time,
            "memory_usage": event.memory_usage,
            "metadata": json.dumps(event.metadata),
            "event_data": msgspec.json.encode(event).decode()
        }
    
    def _deserialize_event(self, row: Dict[str, Any]) -> TaskEvent:
        """Deserialize an event from database storage."""
        # Use the stored msgspec data for accurate deserialization
        return msgspec.json.decode(row["event_data"], type=TaskEvent)
    
    async def log_event(self, event: TaskEvent) -> None:
        """Log a task event."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        event_data = self._serialize_event(event)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.schema}.{self.events_table} (
                    id, task_id, event_type, timestamp, message, details,
                    worker_id, queue_name, schedule_id, error_type, error_message,
                    traceback, execution_time, memory_usage, metadata, event_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                event_data["id"], event_data["task_id"], event_data["event_type"],
                event_data["timestamp"], event_data["message"], event_data["details"],
                event_data["worker_id"], event_data["queue_name"], event_data["schedule_id"],
                event_data["error_type"], event_data["error_message"], event_data["traceback"],
                event_data["execution_time"], event_data["memory_usage"], event_data["metadata"],
                event_data["event_data"]
            )
    
    async def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get task events."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        query = f"SELECT * FROM {self.schema}.{self.events_table} WHERE 1=1"
        params = []
        param_count = 0
        
        if task_id is not None:
            param_count += 1
            query += f" AND task_id = ${param_count}"
            params.append(task_id)
        
        if event_type is not None:
            param_count += 1
            query += f" AND event_type = ${param_count}"
            params.append(event_type)
        
        if start_time is not None:
            param_count += 1
            query += f" AND timestamp >= ${param_count}"
            params.append(start_time)
        
        if end_time is not None:
            param_count += 1
            query += f" AND timestamp <= ${param_count}"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC"
        
        if limit is not None:
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
        
        if offset > 0:
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            events = []
            for row in rows:
                event_dict = dict(row)
                events.append(self._deserialize_event(event_dict))
            
            return events
    
    async def cleanup_old_events(self, older_than: datetime) -> int:
        """Clean up old events."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.events_table} WHERE timestamp < $1",
                older_than
            )
            
            return int(result.split()[-1])  # Extract number of affected rows


class PostgresEventStorage(AsyncPostgresEventStorage):
    """
    Synchronous wrapper around AsyncPostgresEventStorage.
    
    This class provides a synchronous interface to the async PostgreSQL event storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the PostgreSQL database (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from the PostgreSQL database (sync)."""
        asyncio.run(self.disconnect())
    
    def log_event_sync(self, event: TaskEvent) -> None:
        """Log a task event (sync)."""
        asyncio.run(self.log_event(event))
    
    def get_events_sync(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[TaskEvent]:
        """Get task events (sync)."""
        return asyncio.run(self.get_events(task_id, event_type, start_time, end_time, limit, offset))
    
    def cleanup_old_events_sync(self, older_than: datetime) -> int:
        """Clean up old events (sync)."""
        return asyncio.run(self.cleanup_old_events(older_than))
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()


class AsyncPostgresScheduleStorage(BaseScheduleStorage):
    """
    Async PostgreSQL-based schedule storage implementation.
    
    This class implements the BaseScheduleStorage interface using PostgreSQL
    for persistent schedule storage and management.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "omniq",
        username: str = "postgres",
        password: str = "",
        min_connections: int = 1,
        max_connections: int = 10,
        command_timeout: float = 60.0,
        schema: str = "public",
        schedules_table: str = "schedules",
        **kwargs
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.command_timeout = command_timeout
        self.schema = schema
        self.schedules_table = schedules_table
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Connect to the PostgreSQL database."""
        if self._pool is not None:
            return
        
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password,
            min_size=self.min_connections,
            max_size=self.max_connections,
            command_timeout=self.command_timeout,
        )
        
        # Create schema if it doesn't exist
        async with self._pool.acquire() as conn:
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
            
            # Create schedules table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{self.schedules_table} (
                    id TEXT PRIMARY KEY,
                    schedule_type TEXT NOT NULL,
                    func TEXT NOT NULL,
                    args JSONB NOT NULL DEFAULT '[]',
                    kwargs JSONB NOT NULL DEFAULT '{{}}',
                    queue_name TEXT NOT NULL DEFAULT 'default',
                    cron_expression TEXT,
                    interval_seconds REAL,
                    timestamp TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL,
                    last_run TIMESTAMPTZ,
                    next_run TIMESTAMPTZ,
                    max_runs INTEGER,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    ttl_seconds REAL,
                    expires_at TIMESTAMPTZ,
                    metadata JSONB NOT NULL DEFAULT '{{}}',
                    schedule_data JSONB NOT NULL
                )
            """)
            
            # Create indexes for performance
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.schedules_table}_status
                ON {self.schema}.{self.schedules_table}(status)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.schedules_table}_next_run
                ON {self.schema}.{self.schedules_table}(next_run)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.schedules_table}_expires_at
                ON {self.schema}.{self.schedules_table}(expires_at)
            """)
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.schedules_table}_ready
                ON {self.schema}.{self.schedules_table}(status, next_run)
            """)
    
    async def disconnect(self) -> None:
        """Disconnect from the PostgreSQL database."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
    
    def _serialize_schedule(self, schedule: Schedule) -> Dict[str, Any]:
        """Serialize a schedule for database storage."""
        return {
            "id": schedule.id,
            "schedule_type": schedule.schedule_type.value,
            "func": str(schedule.func),
            "args": json.dumps(schedule.args),
            "kwargs": json.dumps(schedule.kwargs),
            "queue_name": schedule.queue_name,
            "cron_expression": schedule.cron_expression,
            "interval_seconds": schedule.interval.total_seconds() if schedule.interval else None,
            "timestamp": schedule.timestamp,
            "status": schedule.status.value,
            "created_at": schedule.created_at,
            "last_run": schedule.last_run,
            "next_run": schedule.next_run,
            "max_runs": schedule.max_runs,
            "run_count": schedule.run_count,
            "ttl_seconds": schedule.ttl.total_seconds() if schedule.ttl else None,
            "expires_at": schedule.expires_at,
            "metadata": json.dumps(schedule.metadata),
            "schedule_data": msgspec.json.encode(schedule).decode()
        }
    
    def _deserialize_schedule(self, row: Dict[str, Any]) -> Schedule:
        """Deserialize a schedule from database storage."""
        # Use the stored msgspec data for accurate deserialization
        return msgspec.json.decode(row["schedule_data"], type=Schedule)
    
    async def save_schedule(self, schedule: Schedule) -> None:
        """Save a schedule."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        schedule_data = self._serialize_schedule(schedule)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO {self.schema}.{self.schedules_table} (
                    id, schedule_type, func, args, kwargs, queue_name,
                    cron_expression, interval_seconds, timestamp, status,
                    created_at, last_run, next_run, max_runs, run_count,
                    ttl_seconds, expires_at, metadata, schedule_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (id) DO UPDATE SET
                    schedule_type = EXCLUDED.schedule_type,
                    func = EXCLUDED.func,
                    args = EXCLUDED.args,
                    kwargs = EXCLUDED.kwargs,
                    queue_name = EXCLUDED.queue_name,
                    cron_expression = EXCLUDED.cron_expression,
                    interval_seconds = EXCLUDED.interval_seconds,
                    timestamp = EXCLUDED.timestamp,
                    status = EXCLUDED.status,
                    last_run = EXCLUDED.last_run,
                    next_run = EXCLUDED.next_run,
                    max_runs = EXCLUDED.max_runs,
                    run_count = EXCLUDED.run_count,
                    ttl_seconds = EXCLUDED.ttl_seconds,
                    expires_at = EXCLUDED.expires_at,
                    metadata = EXCLUDED.metadata,
                    schedule_data = EXCLUDED.schedule_data
            """,
                schedule_data["id"], schedule_data["schedule_type"], schedule_data["func"],
                schedule_data["args"], schedule_data["kwargs"], schedule_data["queue_name"],
                schedule_data["cron_expression"], schedule_data["interval_seconds"],
                schedule_data["timestamp"], schedule_data["status"], schedule_data["created_at"],
                schedule_data["last_run"], schedule_data["next_run"], schedule_data["max_runs"],
                schedule_data["run_count"], schedule_data["ttl_seconds"], schedule_data["expires_at"],
                schedule_data["metadata"], schedule_data["schedule_data"]
            )
    
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM {self.schema}.{self.schedules_table} WHERE id = $1",
                schedule_id
            )
            
            if row is None:
                return None
            
            schedule_dict = dict(row)
            return self._deserialize_schedule(schedule_dict)
    
    async def update_schedule(self, schedule: Schedule) -> None:
        """Update a schedule."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        schedule_data = self._serialize_schedule(schedule)
        
        async with self._pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE {self.schema}.{self.schedules_table} SET
                    schedule_type = $2, func = $3, args = $4, kwargs = $5, queue_name = $6,
                    cron_expression = $7, interval_seconds = $8, timestamp = $9, status = $10,
                    last_run = $11, next_run = $12, max_runs = $13, run_count = $14,
                    ttl_seconds = $15, expires_at = $16, metadata = $17, schedule_data = $18
                WHERE id = $1
            """,
                schedule.id, schedule_data["schedule_type"], schedule_data["func"], schedule_data["args"],
                schedule_data["kwargs"], schedule_data["queue_name"], schedule_data["cron_expression"],
                schedule_data["interval_seconds"], schedule_data["timestamp"], schedule_data["status"],
                schedule_data["last_run"], schedule_data["next_run"], schedule_data["max_runs"],
                schedule_data["run_count"], schedule_data["ttl_seconds"], schedule_data["expires_at"],
                schedule_data["metadata"], schedule_data["schedule_data"]
            )
    
    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.schedules_table} WHERE id = $1",
                schedule_id
            )
            
            return result.split()[-1] != "0"  # Check if any rows were affected
    
    async def list_schedules(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        query = f"SELECT * FROM {self.schema}.{self.schedules_table} WHERE 1=1"
        params = []
        param_count = 0
        
        if status is not None:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit is not None:
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
        
        if offset > 0:
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            schedules = []
            for row in rows:
                schedule_dict = dict(row)
                schedules.append(self._deserialize_schedule(schedule_dict))
            
            return schedules
    
    async def get_ready_schedules(self) -> List[Schedule]:
        """Get schedules that are ready to run."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        now = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT * FROM {self.schema}.{self.schedules_table}
                WHERE status = 'active'
                AND next_run IS NOT NULL
                AND next_run <= $1
                AND (expires_at IS NULL OR expires_at > $1)
                ORDER BY next_run ASC
            """, now)
            
            schedules = []
            for row in rows:
                schedule_dict = dict(row)
                schedules.append(self._deserialize_schedule(schedule_dict))
            
            return schedules
    
    async def cleanup_expired_schedules(self) -> int:
        """Clean up expired schedules."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        
        now = datetime.utcnow()
        
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.schema}.{self.schedules_table} WHERE expires_at IS NOT NULL AND expires_at <= $1",
                now
            )
            
            return int(result.split()[-1])  # Extract number of affected rows


class PostgresScheduleStorage(AsyncPostgresScheduleStorage):
    """
    Synchronous wrapper around AsyncPostgresScheduleStorage.
    
    This class provides a synchronous interface to the async PostgreSQL schedule storage
    implementation using asyncio for thread-safe execution.
    """
    
    def connect_sync(self) -> None:
        """Connect to the PostgreSQL database (sync)."""
        asyncio.run(self.connect())
    
    def disconnect_sync(self) -> None:
        """Disconnect from the PostgreSQL database (sync)."""
        asyncio.run(self.disconnect())
    
    def save_schedule_sync(self, schedule: Schedule) -> None:
        """Save a schedule (sync)."""
        asyncio.run(self.save_schedule(schedule))
    
    def get_schedule_sync(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by ID (sync)."""
        return asyncio.run(self.get_schedule(schedule_id))
    
    def update_schedule_sync(self, schedule: Schedule) -> None:
        """Update a schedule (sync)."""
        asyncio.run(self.update_schedule(schedule))
    
    def delete_schedule_sync(self, schedule_id: str) -> bool:
        """Delete a schedule (sync)."""
        return asyncio.run(self.delete_schedule(schedule_id))
    
    def list_schedules_sync(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Schedule]:
        """List schedules (sync)."""
        return asyncio.run(self.list_schedules(status, limit, offset))
    
    def get_ready_schedules_sync(self) -> List[Schedule]:
        """Get schedules that are ready to run (sync)."""
        return asyncio.run(self.get_ready_schedules())
    
    def cleanup_expired_schedules_sync(self) -> int:
        """Clean up expired schedules (sync)."""
        return asyncio.run(self.cleanup_expired_schedules())
    
    def __enter__(self):
        """Sync context manager entry."""
        self.connect_sync()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.disconnect_sync()