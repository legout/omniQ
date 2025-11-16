"""SQLite-based storage backend for OmniQ tasks and results."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..models import Task, TaskResult, TaskStatus, Schedule
from .base import BaseStorage, Serializer, TaskError


class SQLiteStorage(BaseStorage):
    """SQLite-based storage implementation for OmniQ tasks and results.

    Uses sqlite3 with async wrapper methods for database operations.
    """

    def __init__(
        self,
        db_path: Path,
        serializer: Serializer,
    ):
        self.db_path = Path(db_path)
        self.serializer = serializer

        # Initialize database schema synchronously
        self._initialize_schema_sync()

    def _initialize_schema_sync(self) -> None:
        """Initialize database schema synchronously."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        try:
            self._create_schema(conn)
        finally:
            conn.close()

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        """Create the database schema for tasks and results."""
        # Create tasks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                func_path TEXT NOT NULL,
                args TEXT NOT NULL,
                kwargs TEXT NOT NULL,
                eta TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt INTEGER NOT NULL DEFAULT 1,
                max_retries INTEGER NOT NULL DEFAULT 0,
                timeout INTEGER,
                interval INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)

        # Create results table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT,
                attempt INTEGER NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        """)

        # Create indexes for efficient queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_eta 
            ON tasks (eta) WHERE status = 'pending'
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status 
            ON tasks (status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_task_id 
            ON results (task_id)
        """)

        conn.commit()

    async def enqueue(self, task: Task) -> str:
        """Add a task to the queue."""
        await self._run_db_operation(self._insert_task, task)
        return task.id

    def _insert_task(self, conn: sqlite3.Connection, task: Task) -> None:
        """Insert a task into the database."""
        conn.execute(
            """
            INSERT INTO tasks (
                id, func_path, args, kwargs, eta, status, attempt, 
                max_retries, timeout, interval, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task.id,
                task.func_path,
                json.dumps(task.args),
                json.dumps(task.kwargs),
                task.schedule.eta.isoformat(),
                task.status.value,
                task.attempt,
                task.schedule.max_retries,
                task.schedule.timeout,
                task.schedule.interval,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                json.dumps(task.metadata),
            ),
        )
        conn.commit()

    async def dequeue(self, now: datetime) -> Optional[Task]:
        """Get the next due task from the queue."""
        return await self._run_db_operation(self._get_next_task, now)

    def _get_next_task(self, conn: sqlite3.Connection, now: datetime) -> Optional[Task]:
        """Get the next due task with atomic claiming."""
        cursor = conn.cursor()

        # Find the next due task with proper ordering
        cursor.execute(
            """
            SELECT id, func_path, args, kwargs, eta, status, attempt,
                   max_retries, timeout, interval, created_at, updated_at, metadata
            FROM tasks
            WHERE status = 'pending' AND eta <= ?
            ORDER BY eta ASC, created_at ASC
            LIMIT 1
        """,
            (now.isoformat(),),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Try to atomically claim the task
        cursor.execute(
            """
            UPDATE tasks 
            SET status = 'running', updated_at = ?
            WHERE id = ? AND status = 'pending'
        """,
            (datetime.now(timezone.utc).isoformat(), row[0]),
        )

        if cursor.rowcount == 0:
            # Task was claimed by another process, try again
            conn.rollback()
            return None

        conn.commit()

        # Reconstruct the task
        return Task(
            id=row[0],
            func_path=row[1],
            args=json.loads(row[2]),
            kwargs=json.loads(row[3]),
            schedule=Schedule(
                eta=datetime.fromisoformat(row[4]).replace(tzinfo=timezone.utc),
                max_retries=row[7],
                timeout=row[8],
                interval=row[9],
            ),
            status=TaskStatus(row[5]),
            attempt=row[6],
            created_at=datetime.fromisoformat(row[10]).replace(tzinfo=timezone.utc),
            updated_at=datetime.fromisoformat(row[11]).replace(tzinfo=timezone.utc),
            metadata=json.loads(row[12]),
        )

    def _update_task_status(
        self, conn: sqlite3.Connection, task_id: str, status: TaskStatus
    ) -> None:
        """Update task status in database."""
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, updated_at = ?
            WHERE id = ?
        """,
            (status.value, datetime.now(timezone.utc).isoformat(), task_id),
        )
        conn.commit()

    async def mark_running(self, task_id: str) -> None:
        """Mark a task as running."""
        await self._run_db_operation(
            self._update_task_status, task_id, TaskStatus.RUNNING
        )

    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """Mark a task as completed successfully."""
        await self._run_db_operation(self._complete_task, task_id, result)

    def _complete_task(
        self, conn: sqlite3.Connection, task_id: str, result: TaskResult
    ) -> None:
        """Complete a task and save its result."""
        cursor = conn.cursor()

        # Update task status to success
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, updated_at = ?
            WHERE id = ?
        """,
            (TaskStatus.SUCCESS.value, datetime.now(timezone.utc).isoformat(), task_id),
        )

        # Insert result
        cursor.execute(
            """
            INSERT OR REPLACE INTO results (
                task_id, status, result, error, attempt, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.task_id,
                result.status.value,
                json.dumps(result.result) if result.result is not None else None,
                str(result.error) if result.error else None,
                result.attempt,
                result.started_at.isoformat() if result.started_at else None,
                result.completed_at.isoformat() if result.completed_at else None,
            ),
        )

        conn.commit()

    async def mark_failed(
        self, task_id: str, error: TaskError, will_retry: bool
    ) -> None:
        """Mark a task as failed."""
        await self._run_db_operation(self._fail_task, task_id, error, will_retry)

    def _fail_task(
        self, conn: sqlite3.Connection, task_id: str, error: TaskError, will_retry: bool
    ) -> None:
        """Mark a task as failed and save error result."""
        cursor = conn.cursor()

        # Update task status
        status = TaskStatus.RETRYING if will_retry else TaskStatus.FAILED
        cursor.execute(
            """
            UPDATE tasks 
            SET status = ?, updated_at = ?
            WHERE id = ?
        """,
            (status.value, datetime.now(timezone.utc).isoformat(), task_id),
        )

        # Insert error result
        cursor.execute(
            """
            INSERT OR REPLACE INTO results (
                task_id, status, error, attempt, completed_at
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (
                task_id,
                status.value,
                str(error.error),
                1,  # Will be updated by caller if needed
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        conn.commit()

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve the result of a completed task."""
        return await self._run_db_operation(self._get_task_result, task_id)

    def _get_task_result(
        self, conn: sqlite3.Connection, task_id: str
    ) -> Optional[TaskResult]:
        """Get task result from database."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT task_id, status, result, error, attempt, started_at, completed_at
            FROM results
            WHERE task_id = ?
        """,
            (task_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return TaskResult(
            task_id=row[0],
            status=TaskStatus(row[1]),
            result=json.loads(row[2]) if row[2] is not None else None,
            error=Exception(row[3]) if row[3] else None,
            attempt=row[4],
            started_at=datetime.fromisoformat(row[5]).replace(tzinfo=timezone.utc)
            if row[5]
            else None,
            completed_at=datetime.fromisoformat(row[6]).replace(tzinfo=timezone.utc)
            if row[6]
            else None,
        )

    async def purge_results(self, older_than: datetime) -> int:
        """Remove old task results to save space."""
        return await self._run_db_operation(self._purge_old_results, older_than)

    def _purge_old_results(self, conn: sqlite3.Connection, older_than: datetime) -> int:
        """Purge old results from database."""
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM results
            WHERE completed_at < ? OR completed_at IS NULL
        """,
            (older_than.isoformat(),),
        )

        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Reschedule a task to run at a different time."""
        await self._run_db_operation(self._reschedule_task, task_id, new_eta)

    def _reschedule_task(
        self, conn: sqlite3.Connection, task_id: str, new_eta: datetime
    ) -> None:
        """Reschedule a task in the database."""
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE tasks 
            SET eta = ?, status = 'pending', updated_at = ?
            WHERE id = ?
        """,
            (new_eta.isoformat(), datetime.now(timezone.utc).isoformat(), task_id),
        )

        if cursor.rowcount == 0:
            raise FileNotFoundError(f"Task {task_id} not found for rescheduling")

        conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        # For this simple implementation, we don't maintain a persistent connection
        # so there's nothing to close explicitly
        pass

    async def _run_db_operation(self, operation, *args):
        """Run a database operation in a thread pool."""

        def _db_operation():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                return operation(conn, *args)
            finally:
                conn.close()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)
