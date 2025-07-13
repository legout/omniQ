"""SQLite storage implementations for tasks, results, and events."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import aiosqlite

from ..config.loader import LoggingConfig
from ..models.event import TaskEvent
from ..models.result import TaskResult
from ..models.task import Task
from ..serialization import SerializationManager, MsgspecSerializer, DillSerializer
from .base import BaseTaskQueue, BaseResultStorage, BaseEventStorage


class SQLiteTaskQueue(BaseTaskQueue):
    """SQLite-based task queue supporting both memory and file storage."""
    
    def __init__(
        self,
        database_path: str = ":memory:",
        table_prefix: str = "omniq",
        serialization_manager: Optional[SerializationManager] = None
    ):
        """
        Initialize SQLite task queue.
        
        Args:
            database_path: Path to SQLite database or ":memory:" for in-memory
            table_prefix: Prefix for database tables
            serialization_manager: Serialization manager for task data
        """
        self.database_path = database_path
        self.table_prefix = table_prefix
        self.tasks_table = f"{table_prefix}_tasks"
        
        # Initialize serialization
        if serialization_manager is None:
            serialization_manager = SerializationManager()
            serialization_manager.register_serializer(MsgspecSerializer())
            serialization_manager.register_serializer(DillSerializer())
        self.serialization_manager = serialization_manager
        
        self._db: Optional[aiosqlite.Connection] = None
        self._logger = LoggingConfig.get_logger("storage.sqlite.queue")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._disconnect()
    
    async def _connect(self) -> None:
        """Connect to SQLite database and initialize tables."""
        if self._db is not None:
            return
        
        # Create directory if using file database
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        
        # Enable WAL mode for better concurrency (file databases only)
        if self.database_path != ":memory:":
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA synchronous=NORMAL")
        
        # Create tables
        await self._create_tables()
        
        self._logger.debug(f"Connected to SQLite database: {self.database_path}")
    
    async def _disconnect(self) -> None:
        """Disconnect from SQLite database."""
        if self._db:
            await self._db.close()
            self._db = None
            self._logger.debug("Disconnected from SQLite database")
    
    async def _create_tables(self) -> None:
        """Create database tables."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.tasks_table} (
            id TEXT PRIMARY KEY,
            queue_name TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            scheduled_at REAL,
            ttl_expires_at REAL,
            task_data BLOB NOT NULL,
            serializer_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """
        
        # Create indexes separately
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_queue_priority ON {self.tasks_table}(queue_name, priority DESC, created_at)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_scheduled ON {self.tasks_table}(scheduled_at)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_ttl ON {self.tasks_table}(ttl_expires_at)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.tasks_table}_status ON {self.tasks_table}(status)"
        ]
        
        await self._db.execute(create_table_sql)
        
        # Create indexes
        for index_sql in indexes:
            await self._db.execute(index_sql)
        
        await self._db.commit()
    
    async def enqueue(self, task: Task) -> None:
        """Add a task to the queue."""
        # Serialize task
        task_data, serializer_name = self.serialization_manager.serialize(task)
        
        # Calculate TTL expiration
        ttl_expires_at = None
        if task.ttl is not None:
            ttl_expires_at = task.created_at + task.ttl
        
        # Insert task
        insert_sql = f"""
        INSERT INTO {self.tasks_table} 
        (id, queue_name, priority, created_at, scheduled_at, ttl_expires_at, 
         task_data, serializer_name, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self._db.execute(insert_sql, (
            task.id,
            task.queue,
            task.priority,
            task.created_at,
            task.scheduled_at,
            ttl_expires_at,
            task_data,
            serializer_name,
            'pending'
        ))
        await self._db.commit()
        
        self._logger.debug(f"Enqueued task {task.id} to queue '{task.queue}'")
    
    async def dequeue(self, queue_name: str = "default", timeout: Optional[float] = None) -> Optional[Task]:
        """Remove and return a task from the queue."""
        start_time = time.time()
        
        while True:
            # Try to get a task
            task = await self._get_next_task(queue_name)
            if task is not None:
                return task
            
            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return None
                
                # Sleep for a short time before retrying
                await asyncio.sleep(min(0.1, timeout - elapsed))
            else:
                return None
    
    async def _get_next_task(self, queue_name: str) -> Optional[Task]:
        """Get next available task from queue."""
        current_time = time.time()
        
        # Query for next task with proper ordering
        select_sql = f"""
        SELECT id, task_data, serializer_name
        FROM {self.tasks_table}
        WHERE queue_name = ? 
          AND status = 'pending'
          AND (scheduled_at IS NULL OR scheduled_at <= ?)
          AND (ttl_expires_at IS NULL OR ttl_expires_at > ?)
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
        """
        
        async with self._db.execute(select_sql, (queue_name, current_time, current_time)) as cursor:
            row = await cursor.fetchone()
            
            if row is None:
                return None
            
            # Mark task as processing
            update_sql = f"""
            UPDATE {self.tasks_table} 
            SET status = 'processing' 
            WHERE id = ? AND status = 'pending'
            """
            
            await self._db.execute(update_sql, (row['id'],))
            
            # Check if update was successful (handles race conditions)
            if self._db.total_changes == 0:
                return None
            
            await self._db.commit()
            
            # Deserialize and return task
            task = self.serialization_manager.deserialize(
                row['task_data'], 
                row['serializer_name']
            )
            
            self._logger.debug(f"Dequeued task {task.id} from queue '{queue_name}'")
            return task
    
    async def peek(self, queue_name: str = "default", limit: int = 1) -> List[Task]:
        """Look at tasks in queue without removing them."""
        current_time = time.time()
        
        select_sql = f"""
        SELECT task_data, serializer_name
        FROM {self.tasks_table}
        WHERE queue_name = ? 
          AND status = 'pending'
          AND (scheduled_at IS NULL OR scheduled_at <= ?)
          AND (ttl_expires_at IS NULL OR ttl_expires_at > ?)
        ORDER BY priority DESC, created_at ASC
        LIMIT ?
        """
        
        tasks = []
        async with self._db.execute(select_sql, (queue_name, current_time, current_time, limit)) as cursor:
            async for row in cursor:
                task = self.serialization_manager.deserialize(
                    row['task_data'],
                    row['serializer_name']
                )
                tasks.append(task)
        
        return tasks
    
    async def size(self, queue_name: str = "default") -> int:
        """Get the number of tasks in the queue."""
        current_time = time.time()
        
        count_sql = f"""
        SELECT COUNT(*) as count
        FROM {self.tasks_table}
        WHERE queue_name = ? 
          AND status = 'pending'
          AND (scheduled_at IS NULL OR scheduled_at <= ?)
          AND (ttl_expires_at IS NULL OR ttl_expires_at > ?)
        """
        
        async with self._db.execute(count_sql, (queue_name, current_time, current_time)) as cursor:
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    async def clear(self, queue_name: str = "default") -> int:
        """Clear all tasks from the queue and return count of removed tasks."""
        count_sql = f"SELECT COUNT(*) as count FROM {self.tasks_table} WHERE queue_name = ?"
        async with self._db.execute(count_sql, (queue_name,)) as cursor:
            row = await cursor.fetchone()
            count = row['count'] if row else 0
        
        delete_sql = f"DELETE FROM {self.tasks_table} WHERE queue_name = ?"
        await self._db.execute(delete_sql, (queue_name,))
        await self._db.commit()
        
        self._logger.info(f"Cleared {count} tasks from queue '{queue_name}'")
        return count
    
    async def get_queues(self) -> List[str]:
        """Get list of all queue names."""
        select_sql = f"SELECT DISTINCT queue_name FROM {self.tasks_table}"
        
        queues = []
        async with self._db.execute(select_sql) as cursor:
            async for row in cursor:
                queues.append(row['queue_name'])
        
        return queues
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a specific task by ID."""
        select_sql = f"""
        SELECT task_data, serializer_name
        FROM {self.tasks_table}
        WHERE id = ?
        """
        
        async with self._db.execute(select_sql, (task_id,)) as cursor:
            row = await cursor.fetchone()
            
            if row is None:
                return None
            
            return self.serialization_manager.deserialize(
                row['task_data'],
                row['serializer_name']
            )
    
    async def update_task(self, task: Task) -> bool:
        """Update an existing task."""
        # Serialize updated task
        task_data, serializer_name = self.serialization_manager.serialize(task)
        
        # Calculate TTL expiration
        ttl_expires_at = None
        if task.ttl is not None:
            ttl_expires_at = task.created_at + task.ttl
        
        update_sql = f"""
        UPDATE {self.tasks_table}
        SET queue_name = ?, priority = ?, scheduled_at = ?, ttl_expires_at = ?,
            task_data = ?, serializer_name = ?
        WHERE id = ?
        """
        
        await self._db.execute(update_sql, (
            task.queue,
            task.priority,
            task.scheduled_at,
            ttl_expires_at,
            task_data,
            serializer_name,
            task.id
        ))
        await self._db.commit()
        
        return self._db.total_changes > 0
    
    async def remove_task(self, task_id: str) -> bool:
        """Remove a specific task by ID."""
        delete_sql = f"DELETE FROM {self.tasks_table} WHERE id = ?"
        await self._db.execute(delete_sql, (task_id,))
        await self._db.commit()
        
        return self._db.total_changes > 0
    
    async def list_tasks(
        self,
        queue_name: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """List tasks with optional filtering."""
        where_clauses = []
        params = []
        
        if queue_name:
            where_clauses.append("queue_name = ?")
            params.append(queue_name)
        
        if filters:
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""
        
        select_sql = f"""
        SELECT task_data, serializer_name
        FROM {self.tasks_table}
        {where_clause}
        ORDER BY created_at DESC
        {limit_clause} {offset_clause}
        """
        
        tasks = []
        async with self._db.execute(select_sql, params) as cursor:
            async for row in cursor:
                task = self.serialization_manager.deserialize(
                    row['task_data'],
                    row['serializer_name']
                )
                tasks.append(task)
        
        return tasks
    
    async def count_tasks(
        self,
        queue_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count tasks with optional filtering."""
        where_clauses = []
        params = []
        
        if queue_name:
            where_clauses.append("queue_name = ?")
            params.append(queue_name)
        
        if filters:
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        count_sql = f"""
        SELECT COUNT(*) as count
        FROM {self.tasks_table}
        {where_clause}
        """
        
        async with self._db.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    async def cleanup_expired_tasks(self) -> int:
        """Remove expired tasks and return count."""
        current_time = time.time()
        
        # Count expired tasks
        count_sql = f"""
        SELECT COUNT(*) as count
        FROM {self.tasks_table}
        WHERE ttl_expires_at IS NOT NULL AND ttl_expires_at <= ?
        """
        
        async with self._db.execute(count_sql, (current_time,)) as cursor:
            row = await cursor.fetchone()
            count = row['count'] if row else 0
        
        # Delete expired tasks
        delete_sql = f"""
        DELETE FROM {self.tasks_table}
        WHERE ttl_expires_at IS NOT NULL AND ttl_expires_at <= ?
        """
        
        await self._db.execute(delete_sql, (current_time,))
        await self._db.commit()
        
        if count > 0:
            self._logger.info(f"Cleaned up {count} expired tasks")
        
        return count
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        if self._db is None:
            return {"status": "disconnected"}
        
        try:
            # Test database connection
            async with self._db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            
            # Get statistics
            stats_sql = f"""
            SELECT 
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
                COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_tasks,
                COUNT(DISTINCT queue_name) as queue_count
            FROM {self.tasks_table}
            """
            
            async with self._db.execute(stats_sql) as cursor:
                row = await cursor.fetchone()
                stats = dict(row) if row else {}
            
            return {
                "status": "healthy",
                "database_path": self.database_path,
                "table_prefix": self.table_prefix,
                **stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class SQLiteResultStorage(BaseResultStorage):
    """SQLite-based result storage supporting both memory and file storage."""
    
    def __init__(
        self,
        database_path: str = ":memory:",
        table_prefix: str = "omniq",
        serialization_manager: Optional[SerializationManager] = None
    ):
        """
        Initialize SQLite result storage.
        
        Args:
            database_path: Path to SQLite database or ":memory:" for in-memory
            table_prefix: Prefix for database tables
            serialization_manager: Serialization manager for result data
        """
        self.database_path = database_path
        self.table_prefix = table_prefix
        self.results_table = f"{table_prefix}_results"
        
        # Initialize serialization
        if serialization_manager is None:
            serialization_manager = SerializationManager()
            serialization_manager.register_serializer(MsgspecSerializer())
            serialization_manager.register_serializer(DillSerializer())
        self.serialization_manager = serialization_manager
        
        self._db: Optional[aiosqlite.Connection] = None
        self._logger = LoggingConfig.get_logger("storage.sqlite.results")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._disconnect()
    
    async def _connect(self) -> None:
        """Connect to SQLite database and initialize tables."""
        if self._db is not None:
            return
        
        # Create directory if using file database
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._db = await aiosqlite.connect(self.database_path)
        self._db.row_factory = aiosqlite.Row
        
        # Enable WAL mode for better concurrency (file databases only)
        if self.database_path != ":memory:":
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA synchronous=NORMAL")
        
        # Create tables
        await self._create_tables()
        
        self._logger.debug(f"Connected to SQLite database: {self.database_path}")
    
    async def _disconnect(self) -> None:
        """Disconnect from SQLite database."""
        if self._db:
            await self._db.close()
            self._db = None
            self._logger.debug("Disconnected from SQLite database")
    
    async def _create_tables(self) -> None:
        """Create database tables."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.results_table} (
            task_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            started_at REAL NOT NULL,
            completed_at REAL NOT NULL,
            duration REAL,
            worker_id TEXT,
            worker_type TEXT,
            result_data BLOB,
            result_serializer TEXT,
            error_type TEXT,
            error_message TEXT,
            error_traceback TEXT,
            execution_attempts INTEGER DEFAULT 1,
            created_at REAL NOT NULL DEFAULT (unixepoch('subsec'))
        )
        """
        
        # Create indexes separately
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_{self.results_table}_status ON {self.results_table}(status)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.results_table}_completed ON {self.results_table}(completed_at)",
            f"CREATE INDEX IF NOT EXISTS idx_{self.results_table}_worker ON {self.results_table}(worker_id)"
        ]
        
        await self._db.execute(create_table_sql)
        
        # Create indexes
        for index_sql in indexes:
            await self._db.execute(index_sql)
        
        await self._db.commit()
    
    async def store_result(self, result: TaskResult) -> None:
        """Store a task result."""
        # Serialize result data if present
        result_data = None
        result_serializer = None
        
        if result.result is not None:
            result_data, result_serializer = self.serialization_manager.serialize(result.result)
        
        # Extract error information
        error_type = None
        error_message = None
        error_traceback = None
        
        if result.error:
            error_type = result.error.error_type
            error_message = result.error.error_message
            error_traceback = result.error.traceback
        
        # Insert or replace result
        insert_sql = f"""
        INSERT OR REPLACE INTO {self.results_table}
        (task_id, status, started_at, completed_at, duration, worker_id, worker_type,
         result_data, result_serializer, error_type, error_message, error_traceback,
         execution_attempts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await self._db.execute(insert_sql, (
            result.task_id,
            result.status,
            result.started_at,
            result.completed_at,
            result.duration,
            result.worker_id,
            result.worker_type,
            result_data,
            result_serializer,
            error_type,
            error_message,
            error_traceback,
            result.execution_attempts
        ))
        await self._db.commit()
        
        self._logger.debug(f"Stored result for task {result.task_id}")
    
    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get a task result by task ID."""
        select_sql = f"""
        SELECT task_id, status, started_at, completed_at, duration, worker_id, worker_type,
               result_data, result_serializer, error_type, error_message, error_traceback,
               execution_attempts
        FROM {self.results_table}
        WHERE task_id = ?
        """
        
        async with self._db.execute(select_sql, (task_id,)) as cursor:
            row = await cursor.fetchone()
            
            if row is None:
                return None
            
            # Deserialize result data
            result_value = None
            if row['result_data'] and row['result_serializer']:
                result_value = self.serialization_manager.deserialize(
                    row['result_data'],
                    row['result_serializer']
                )
            
            # Reconstruct error if present
            error = None
            if row['error_type']:
                from ..models.result import TaskError
                error = TaskError(
                    error_type=row['error_type'],
                    error_message=row['error_message'] or "",
                    traceback=row['error_traceback']
                )
            
            return TaskResult(
                task_id=row['task_id'],
                worker_id=row['worker_id'],
                status=row['status'],
                result=result_value,
                error=error,
                started_at=row['started_at'],
                completed_at=row['completed_at'],
                duration=row['duration'],
                worker_type=row['worker_type'],
                execution_attempts=row['execution_attempts']
            )
    
    async def delete_result(self, task_id: str) -> bool:
        """Delete a task result."""
        delete_sql = f"DELETE FROM {self.results_table} WHERE task_id = ?"
        await self._db.execute(delete_sql, (task_id,))
        await self._db.commit()
        
        return self._db.total_changes > 0
    
    async def list_results(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[TaskResult]:
        """List results with optional filtering."""
        where_clauses = []
        params = []
        
        if filters:
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
            
            if 'worker_id' in filters:
                where_clauses.append("worker_id = ?")
                params.append(filters['worker_id'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""
        
        select_sql = f"""
        SELECT task_id, status, started_at, completed_at, duration, worker_id, worker_type,
               result_data, result_serializer, error_type, error_message, error_traceback,
               execution_attempts
        FROM {self.results_table}
        {where_clause}
        ORDER BY completed_at DESC
        {limit_clause} {offset_clause}
        """
        
        results = []
        async with self._db.execute(select_sql, params) as cursor:
            async for row in cursor:
                # Deserialize result data
                result_value = None
                if row['result_data'] and row['result_serializer']:
                    result_value = self.serialization_manager.deserialize(
                        row['result_data'],
                        row['result_serializer']
                    )
                
                # Reconstruct error if present
                error = None
                if row['error_type']:
                    from ..models.result import TaskError
                    error = TaskError(
                        error_type=row['error_type'],
                        error_message=row['error_message'] or "",
                        traceback=row['error_traceback']
                    )
                
                result = TaskResult(
                    task_id=row['task_id'],
                    worker_id=row['worker_id'],
                    status=row['status'],
                    result=result_value,
                    error=error,
                    started_at=row['started_at'],
                    completed_at=row['completed_at'],
                    duration=row['duration'],
                    worker_type=row['worker_type'],
                    execution_attempts=row['execution_attempts']
                )
                results.append(result)
        
        return results
    
    async def count_results(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count results with optional filtering."""
        where_clauses = []
        params = []
        
        if filters:
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        count_sql = f"""
        SELECT COUNT(*) as count
        FROM {self.results_table}
        {where_clause}
        """
        
        async with self._db.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    async def get_results_by_status(self, status: str) -> List[TaskResult]:
        """Get results by status."""
        return await self.list_results(filters={'status': status})
    
    async def cleanup_expired_results(self) -> int:
        """Remove expired results and return count."""
        # For now, we don't implement TTL for results in this basic version
        # This would require adding TTL columns and logic
        return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check and return status."""
        if self._db is None:
            return {"status": "disconnected"}
        
        try:
            # Test database connection
            async with self._db.execute("SELECT 1") as cursor:
                await cursor.fetchone()
            
            # Get statistics
            stats_sql = f"""
            SELECT 
                COUNT(*) as total_results,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN status = 'failure' THEN 1 END) as failure_count,
                AVG(duration) as avg_duration
            FROM {self.results_table}
            """
            
            async with self._db.execute(stats_sql) as cursor:
                row = await cursor.fetchone()
                stats = dict(row) if row else {}
            
            return {
                "status": "healthy",
                "database_path": self.database_path,
                "table_prefix": self.table_prefix,
                **stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }