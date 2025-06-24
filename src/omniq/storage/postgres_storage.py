"""
PostgreSQL storage backend for OmniQ tasks, results, and events.
"""

import asyncio
import json
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import asyncpg
from asyncpg.pool import Pool
from asyncpg.transaction import Transaction

from omniq.models.task import Task
from omniq.models.task_result import TaskResult
from omniq.models.task_event import TaskEvent
from omniq.storage.base import BaseTaskStorage, BaseResultStorage, BaseEventStorage
from omniq.serialization.manager import SerializationManager


class PostgresTaskStorage(BaseTaskStorage):
    """PostgreSQL task storage implementation with async and sync interfaces."""

    def __init__(
        self,
        dsn: str,
        min_pool_size: int = 1,
        max_pool_size: int = 20,
        serializer: Optional[SerializationManager] = None,
    ):
        """
        Initialize PostgreSQL task storage.

        Args:
            dsn: PostgreSQL connection string
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
            serializer: Serialization manager for tasks
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.serializer = serializer or SerializationManager()
        self.pool: Pool | None = None
        self._lock = asyncio.Lock()
        # Initialize pool immediately to avoid None checks
        try:
            asyncio.run(self.initialize())
        except Exception as e:
            print(f"Failed to initialize pool: {e}")
            self.pool = None

    async def initialize(self) -> None:
        """Initialize connection pool and create tables if needed."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
            )
            if self.pool:
                await self._create_tables()

    async def _create_tables(self) -> None:
        """Create tasks and schedules tables if they don't exist."""
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    queue_name TEXT NOT NULL,
                    data BYTEA NOT NULL,
                    format TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    ttl INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_tasks_queue_status 
                ON tasks(queue_name, status);
                
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
                    cron_expression TEXT,
                    interval_seconds INTEGER,
                    specific_timestamp TIMESTAMP WITH TIME ZONE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    last_run TIMESTAMP WITH TIME ZONE,
                    next_run TIMESTAMP WITH TIME ZONE,
                    timezone TEXT NOT NULL DEFAULT 'UTC'
                );
            ''')

    async def shutdown(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def _transaction(self):
        """Async context manager for transactions."""
        if not self.pool:
            await self.initialize()
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        conn = await self.pool.acquire()
        tx = conn.transaction()
        try:
            await tx.start()
            yield conn
            await tx.commit()
        except Exception as e:
            await tx.rollback()
            raise e
        finally:
            await conn.release()

    @contextmanager
    def _sync_transaction(self):
        """Sync context manager for transactions."""
        if not self.pool:
            asyncio.run(self.initialize())
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If an event loop is already running, we can't use asyncio.run
            # Use a future to run the async context manager
            future = asyncio.ensure_future(self._transaction().__aenter__())
            conn = loop.run_until_complete(future)
            try:
                yield conn
                loop.run_until_complete(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                loop.run_until_complete(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise
        else:
            # If no event loop is running, we can use asyncio.run
            conn = asyncio.run(self._transaction().__aenter__())
            try:
                yield conn
                asyncio.run(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                asyncio.run(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise

    async def store_task_async(self, task: Task) -> None:
        """Asynchronously store a task in the backend."""
        serialized_data, format_name = self.serializer.serialize(task)
        now = datetime.utcnow()
        
        async with self._transaction() as conn:
            task_id = task.id
            await conn.execute(
                """
                INSERT INTO tasks (
                    id, queue_name, data, format, created_at, updated_at, ttl, status, dependencies
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    data = $3,
                    format = $4,
                    updated_at = $6,
                    status = $8,
                    dependencies = $9
                """,
                task_id,
                "default",  # Assuming default queue for simplicity
                serialized_data,
                format_name,
                now,
                now,
                task.ttl,
                "pending",
                json.dumps(task.dependencies or []),
            )

    def store_task(self, task: Task) -> None:
        """Synchronously store a task in the backend."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(self.store_task_async(task))
        else:
            asyncio.run(self.store_task_async(task))

    async def get_task_async(self, task_id: str) -> Optional[Task]:
        """Asynchronously retrieve a task by ID."""
        if not self.pool:
            await self.initialize()
            
        if self.pool is None:
            return None
            
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT data, format
                FROM tasks
                WHERE id = $1
                AND (ttl IS NULL OR created_at + INTERVAL '1 second' * ttl > NOW())
                """,
                task_id,
            )
            if record:
                data = record['data']
                format_name = record['format']
                return self.serializer.deserialize(data, format_name)
            return None

    def get_task(self, task_id: str) -> Optional[Task]:
        """Synchronously retrieve a task by ID."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_task_async(task_id))
        else:
            return asyncio.run(self.get_task_async(task_id))

    async def get_tasks_async(self, limit: int = 100) -> List[Task]:
        """Asynchronously retrieve a list of tasks, optionally limited."""
        if not self.pool:
            await self.initialize()
            
        if self.pool is None:
            return []
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT data, format
                FROM tasks
                WHERE (ttl IS NULL OR created_at + INTERVAL '1 second' * ttl > NOW())
                ORDER BY created_at ASC
                LIMIT $1
                """,
                limit,
            )
            return [
                self.serializer.deserialize(row['data'], row['format'])
                for row in rows
            ]

    def get_tasks(self, limit: int = 100) -> List[Task]:
        """Synchronously retrieve a list of tasks, optionally limited."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_tasks_async(limit))
        else:
            return asyncio.run(self.get_tasks_async(limit))

    async def delete_task_async(self, task_id: str) -> bool:
        """Asynchronously delete a task by ID."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                DELETE FROM tasks
                WHERE id = $1
                """,
                task_id,
            )
            return result != "DELETE 0"

    def delete_task(self, task_id: str) -> bool:
        """Synchronously delete a task by ID."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.delete_task_async(task_id))
        else:
            return asyncio.run(self.delete_task_async(task_id))

    async def cleanup_expired_tasks_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired tasks based on TTL."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                DELETE FROM tasks
                WHERE ttl IS NOT NULL
                AND created_at + INTERVAL '1 second' * ttl < $1
                """,
                current_time,
            )
            return int(result.split()[1]) if result != "DELETE 0" else 0

    def cleanup_expired_tasks(self, current_time: datetime) -> int:
        """Synchronously clean up expired tasks based on TTL."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.cleanup_expired_tasks_async(current_time))
        else:
            return asyncio.run(self.cleanup_expired_tasks_async(current_time))

    async def update_schedule_state_async(self, schedule_id: str, active: bool) -> bool:
        """Asynchronously update the state of a schedule (active/paused)."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                UPDATE schedules
                SET is_active = $2
                WHERE id = $1
                """,
                schedule_id,
                active,
            )
            return result != "UPDATE 0"

    def update_schedule_state(self, schedule_id: str, active: bool) -> bool:
        """Synchronously update the state of a schedule (active/paused)."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.update_schedule_state_async(schedule_id, active))
        else:
            return asyncio.run(self.update_schedule_state_async(schedule_id, active))

    async def get_schedule_state_async(self, schedule_id: str) -> Optional[bool]:
        """Asynchronously retrieve the state of a schedule (active/paused)."""
        if not self.pool:
            await self.initialize()
            
        if self.pool is None:
            return None
            
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT is_active
                FROM schedules
                WHERE id = $1
                """,
                schedule_id,
            )
            if record:
                return record['is_active']
            return None

    def get_schedule_state(self, schedule_id: str) -> Optional[bool]:
        """Synchronously retrieve the state of a schedule (active/paused)."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_schedule_state_async(schedule_id))
        else:
            return asyncio.run(self.get_schedule_state_async(schedule_id))


class PostgresResultStorage(BaseResultStorage):
    """PostgreSQL result storage implementation with async and sync interfaces."""

    def __init__(self, dsn: str, min_pool_size: int = 1, max_pool_size: int = 20):
        """
        Initialize PostgreSQL result storage.

        Args:
            dsn: PostgreSQL connection string
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool: Pool | None = None
        self._lock = asyncio.Lock()
        # Initialize pool immediately to avoid None checks
        try:
            asyncio.run(self.initialize())
        except Exception as e:
            print(f"Failed to initialize pool: {e}")
            self.pool = None

    async def initialize(self) -> None:
        """Initialize connection pool and create tables if needed."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
            )
            if self.pool:
                await self._create_tables()

    async def _create_tables(self) -> None:
        """Create results table if it doesn't exist."""
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS results (
                    task_id TEXT PRIMARY KEY,
                    result_data BYTEA NOT NULL,
                    format TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    ttl INTEGER
                );
            ''')

    async def shutdown(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def _transaction(self):
        """Async context manager for transactions."""
        if not self.pool:
            await self.initialize()
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        conn = await self.pool.acquire()
        tx = conn.transaction()
        try:
            await tx.start()
            yield conn
            await tx.commit()
        except Exception as e:
            await tx.rollback()
            raise e
        finally:
            await conn.release()

    @contextmanager
    def _sync_transaction(self):
        """Sync context manager for transactions."""
        if not self.pool:
            asyncio.run(self.initialize())
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.ensure_future(self._transaction().__aenter__())
            conn = loop.run_until_complete(future)
            try:
                yield conn
                loop.run_until_complete(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                loop.run_until_complete(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise
        else:
            conn = asyncio.run(self._transaction().__aenter__())
            try:
                yield conn
                asyncio.run(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                asyncio.run(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise

    async def store_result_async(self, result: TaskResult) -> None:
        """Asynchronously store a task result in the backend."""
        if not self.pool:
            await self.initialize()
            
        serialized_data, format_name = SerializationManager().serialize(result)
        now = datetime.utcnow()
        
        async with self._transaction() as conn:
            await conn.execute(
                """
                INSERT INTO results (task_id, result_data, format, created_at, ttl)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (task_id) DO UPDATE SET
                    result_data = $2,
                    format = $3,
                    created_at = $4,
                    ttl = $5
                """,
                result.task_id,
                serialized_data,
                format_name,
                now,
                result.ttl,
            )

    def store_result(self, result: TaskResult) -> None:
        """Synchronously store a task result in the backend."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(self.store_result_async(result))
        else:
            asyncio.run(self.store_result_async(result))

    async def get_result_async(self, task_id: str) -> Optional[TaskResult]:
        """Asynchronously retrieve a task result by task ID."""
        if not self.pool:
            await self.initialize()
            
        if self.pool is None:
            return None
            
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                SELECT result_data, format
                FROM results
                WHERE task_id = $1
                AND (ttl IS NULL OR created_at + INTERVAL '1 second' * ttl > NOW())
                """,
                task_id,
            )
            if record:
                data = record['result_data']
                format_name = record['format']
                return SerializationManager().deserialize(data, format_name)
            return None

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Synchronously retrieve a task result by task ID."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_result_async(task_id))
        else:
            return asyncio.run(self.get_result_async(task_id))

    async def get_results_async(self, limit: int = 100) -> List[TaskResult]:
        """Asynchronously retrieve a list of task results, optionally limited."""
        if not self.pool:
            await self.initialize()
            
        if self.pool is None:
            return []
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT result_data, format
                FROM results
                WHERE (ttl IS NULL OR created_at + INTERVAL '1 second' * ttl > NOW())
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit,
            )
            serializer = SerializationManager()
            return [
                serializer.deserialize(row['result_data'], row['format'])
                for row in rows
            ]

    def get_results(self, limit: int = 100) -> List[TaskResult]:
        """Synchronously retrieve a list of task results, optionally limited."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_results_async(limit))
        else:
            return asyncio.run(self.get_results_async(limit))

    async def delete_result_async(self, task_id: str) -> bool:
        """Asynchronously delete a task result by task ID."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                DELETE FROM results
                WHERE task_id = $1
                """,
                task_id,
            )
            return result != "DELETE 0"

    def delete_result(self, task_id: str) -> bool:
        """Synchronously delete a task result by task ID."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.delete_result_async(task_id))
        else:
            return asyncio.run(self.delete_result_async(task_id))

    async def cleanup_expired_results_async(self, current_time: datetime) -> int:
        """Asynchronously clean up expired results based on TTL."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                DELETE FROM results
                WHERE ttl IS NOT NULL
                AND created_at + INTERVAL '1 second' * ttl < $1
                """,
                current_time,
            )
            return int(result.split()[1]) if result != "DELETE 0" else 0

    def cleanup_expired_results(self, current_time: datetime) -> int:
        """Synchronously clean up expired results based on TTL."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.cleanup_expired_results_async(current_time))
        else:
            return asyncio.run(self.cleanup_expired_results_async(current_time))


class PostgresEventStorage(BaseEventStorage):
    """PostgreSQL event storage implementation with async and sync interfaces."""

    def __init__(self, dsn: str, min_pool_size: int = 1, max_pool_size: int = 20):
        """
        Initialize PostgreSQL event storage.

        Args:
            dsn: PostgreSQL connection string
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
        """
        self.dsn = dsn
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool: Pool | None = None
        self._lock = asyncio.Lock()
        # Initialize pool immediately to avoid None checks
        try:
            asyncio.run(self.initialize())
        except Exception as e:
            print(f"Failed to initialize pool: {e}")
            self.pool = None

    async def initialize(self) -> None:
        """Initialize connection pool and create tables if needed."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
            )
            if self.pool:
                await self._create_tables()

    async def _create_tables(self) -> None:
        """Create events table if it doesn't exist."""
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
            ''')

    async def shutdown(self) -> None:
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def _transaction(self):
        """Async context manager for transactions."""
        if not self.pool:
            await self.initialize()
        if self.pool is None:
            raise RuntimeError("Database pool is not initialized")
        conn = await self.pool.acquire()
        tx = conn.transaction()
        try:
            await tx.start()
            yield conn
            await tx.commit()
        except Exception as e:
            await tx.rollback()
            raise e
        finally:
            await conn.release()

    @contextmanager
    def _sync_transaction(self):
        """Sync context manager for transactions."""
        if not self.pool:
            asyncio.run(self.initialize())
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.ensure_future(self._transaction().__aenter__())
            conn = loop.run_until_complete(future)
            try:
                yield conn
                loop.run_until_complete(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                loop.run_until_complete(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise
        else:
            conn = asyncio.run(self._transaction().__aenter__())
            try:
                yield conn
                asyncio.run(self._transaction().__aexit__(None, None, None))
            except Exception as e:
                asyncio.run(self._transaction().__aexit__(type(e), e, e.__traceback__))
                raise

    async def log_event_async(self, event: TaskEvent) -> None:
        """Asynchronously log a task event."""
        if not self.pool:
            await self.initialize()
            
        now = datetime.utcnow()
        async with self._transaction() as conn:
            await conn.execute(
                """
                INSERT INTO events (task_id, event_type, timestamp, metadata)
                VALUES ($1, $2, $3, $4)
                """,
                event.task_id,
                event.event_type,
                now,
                json.dumps(event.metadata or {}),
            )

    def log_event(self, event: TaskEvent) -> None:
        """Synchronously log a task event."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.run_until_complete(self.log_event_async(event))
        else:
            asyncio.run(self.log_event_async(event))

    async def get_events_async(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Asynchronously retrieve events, optionally filtered by task ID or event type."""
        if not self.pool:
            await self.initialize()
            
        query = """
            SELECT task_id, event_type, timestamp, metadata
            FROM events
            WHERE 1=1
        """
        params = []
        conditions = []
        
        if task_id:
            params.append(task_id)
            conditions.append(f"task_id = ${len(params)}")
        if event_type:
            params.append(event_type)
            conditions.append(f"event_type = ${len(params)}")
            
        if conditions:
            query += " AND " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC"
        if limit:
            params.append(limit)
            query += f" LIMIT ${len(params)}"
            
        if self.pool is None:
            return []
            
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [
                TaskEvent(
                    task_id=row['task_id'],
                    event_type=row['event_type'],
                    timestamp=row['timestamp'],
                    metadata=row['metadata'],
                )
                for row in rows
            ]

    def get_events(self, task_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[TaskEvent]:
        """Synchronously retrieve events, optionally filtered by task ID or event type."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.get_events_async(task_id, event_type, limit))
        else:
            return asyncio.run(self.get_events_async(task_id, event_type, limit))

    async def cleanup_old_events_async(self, retention_days: int) -> int:
        """Asynchronously clean up old events based on retention policy."""
        if not self.pool:
            await self.initialize()
            
        async with self._transaction() as conn:
            result = await conn.execute(
                """
                DELETE FROM events
                WHERE timestamp < NOW() - INTERVAL '1 day' * $1
                """,
                retention_days,
            )
            return int(result.split()[1]) if result != "DELETE 0" else 0

    def cleanup_old_events(self, retention_days: int) -> int:
        """Synchronously clean up old events based on retention policy."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(self.cleanup_old_events_async(retention_days))
        else:
            return asyncio.run(self.cleanup_old_events_async(retention_days))
