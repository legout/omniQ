from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .base import BaseStorage, NotFoundError, StorageError
from ..models import Task, TaskResult, TaskStatus, transition_status


class SQLiteStorage(BaseStorage):
    """
    SQLite-based storage backend using aiosqlite for async operations.

    Provides a lightweight, transactional store for tasks and results
    with proper indexing for efficient dequeue operations.
    """

    def __init__(self, db_path: str | Path):
        """
        Initialize SQLite storage with database path.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._connection = None

    async def _get_connection(self):
        """Get or create async SQLite connection."""
        if self._connection is None:
            try:
                import aiosqlite

                self._connection = await aiosqlite.connect(self.db_path)
                # Enable WAL mode for better concurrency
                await self._connection.execute("PRAGMA journal_mode=WAL")
                # Enable foreign keys
                await self._connection.execute("PRAGMA foreign_keys=ON")
            except ImportError:
                # Fallback to built-in sqlite3 with async wrapper
                from ._async_sqlite import connect

                self._connection = await connect(self.db_path)
                # Enable WAL mode for better concurrency
                await self._connection.execute("PRAGMA journal_mode=WAL")
                # Enable foreign keys
                await self._connection.execute("PRAGMA foreign_keys=ON")

            await self._migrate()
        return self._connection

    async def _migrate(self) -> None:
        """Create and migrate database schema."""
        conn = await self._get_connection()

        # Create tasks table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                func_path TEXT NOT NULL,
                args TEXT NOT NULL,  -- JSON array
                kwargs TEXT NOT NULL,  -- JSON object
                status TEXT NOT NULL,
                schedule TEXT NOT NULL,  -- JSON object with eta/interval
                eta TEXT,  -- ISO datetime, extracted from schedule for indexing
                max_retries INTEGER NOT NULL,
                timeout INTEGER,  -- seconds, NULL for no timeout
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,  -- ISO datetime
                updated_at TEXT NOT NULL,  -- ISO datetime
                last_attempt_at TEXT,  -- ISO datetime
                error TEXT  -- JSON encoded TaskError
            )
        """)

        # Create results table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                result TEXT,  -- JSON encoded result
                error TEXT,  -- Error message
                finished_at TEXT NOT NULL,  -- ISO datetime
                attempts INTEGER NOT NULL,
                last_attempt_at TEXT,  -- ISO datetime
                FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
            )
        """)

        # Add error field to existing tasks table (migration)
        try:
            await conn.execute("""
                ALTER TABLE tasks ADD COLUMN error TEXT  -- JSON encoded TaskError
            """)
        except Exception:
            # Column already exists, ignore
            pass

        # Create indexes for efficient dequeue
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status_eta 
            ON tasks (status, eta)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_eta 
            ON tasks (eta)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status 
            ON tasks (status)
        """)

        await conn.commit()

    def _serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO string."""
        if dt is None:
            return None
        return dt.isoformat()

    def _deserialize_datetime(
        self, dt_str: Optional[str | bytes | int]
    ) -> Optional[datetime]:
        """Deserialize ISO string to datetime."""
        if dt_str is None or dt_str == 0:
            return None
        if isinstance(dt_str, bytes):
            dt_str = dt_str.decode("utf-8")
        # Handle case where dt_str might already be a datetime object
        if isinstance(dt_str, datetime):
            return dt_str
        # Handle unexpected types (like 0 for NULL values)
        if not isinstance(dt_str, str):
            return None
        # Handle string 'null' which represents NULL in database
        if dt_str == "null" or dt_str.lower() == "null":
            return None
        return datetime.fromisoformat(dt_str)

    def _serialize_json(self, obj: Any) -> str:
        """Serialize object to JSON string."""
        return json.dumps(obj)

    def _deserialize_json(self, json_str: str) -> Any:
        """Deserialize JSON string to object."""
        return json.loads(json_str)

    async def enqueue(self, task: Task) -> str:
        """Persist a task and make it eligible for dequeue when its eta is due."""
        conn = await self._get_connection()

        try:
            # Extract eta and interval from schedule and create serializable copy
            schedule = task["schedule"].copy()
            eta = schedule.get("eta")
            eta_str = self._serialize_datetime(eta) if eta else None
            interval = schedule.get("interval")

            # Serialize datetime and timedelta objects in schedule
            if eta:
                schedule["eta"] = eta_str
            if interval:
                from ..serialization import serialize_timedelta

                schedule["interval"] = serialize_timedelta(interval)

            values = [
                task["id"],
                task["func_path"],
                self._serialize_json(task["args"]),
                self._serialize_json(task["kwargs"]),
                task["status"].value,
                self._serialize_json(schedule),
                eta_str,
                task["max_retries"],
                task["timeout"],
                task["attempts"],
                self._serialize_datetime(task["created_at"]),
                self._serialize_datetime(task["updated_at"]),
                self._serialize_datetime(task["last_attempt_at"]),
                self._serialize_json(
                    task.get("error").to_dict() if task.get("error") else None
                ),
            ]

            await conn.execute(
                """
                    INSERT INTO tasks (
                        id, func_path, args, kwargs, status, schedule, eta,
                        max_retries, timeout, attempts, created_at, updated_at, last_attempt_at, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )

            await conn.commit()
            return task["id"]

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to enqueue task {task['id']}: {e}")

    async def dequeue(self, now: datetime) -> Optional[Task]:
        """Retrieve a single due task, ensuring atomic claim semantics."""
        conn = await self._get_connection()
        now_str = self._serialize_datetime(now)

        try:
            # Start transaction for atomic dequeue
            await conn.execute("BEGIN IMMEDIATE")

            # Find the earliest due PENDING task
            cursor = await conn.execute(
                """
                SELECT id, func_path, args, kwargs, status, schedule, eta,
                       max_retries, timeout, attempts, created_at, updated_at, last_attempt_at, error
                FROM tasks 
                WHERE status = 'PENDING' 
                AND (eta IS NULL OR eta <= ?)
                ORDER BY eta ASC, created_at ASC
                LIMIT 1
            """,
                (now_str,),
            )

            row = await cursor.fetchone()
            if row is None:
                await conn.rollback()
                return None

            # Convert row to Task
            schedule = self._deserialize_json(row[5])
            eta = schedule.get("eta")
            if eta:
                schedule["eta"] = self._deserialize_datetime(eta)

            # Handle interval deserialization
            interval = schedule.get("interval")
            if (
                interval
                and isinstance(interval, dict)
                and interval.get("type") == "timedelta"
            ):
                from ..serialization import deserialize_timedelta

                schedule["interval"] = deserialize_timedelta(interval)

            current_attempts = int(row[9]) if row[9] is not None else 0

            # Update attempts and timestamps based on whether this is a retry
            if current_attempts > 0:
                # For retry tasks, don't increment attempts, just update timestamps
                new_attempts = current_attempts
                new_last_attempt_at = datetime.now(timezone.utc)
            else:
                # For new tasks, increment attempts and update timestamps
                new_attempts = current_attempts + 1
                new_last_attempt_at = datetime.now(timezone.utc)

            # Single atomic UPDATE to set status, attempts, and timestamps
            await conn.execute(
                """
                    UPDATE tasks 
                    SET status = 'RUNNING', attempts = ?, last_attempt_at = ?, updated_at = ?
                    WHERE id = ?
                """,
                (
                    new_attempts,
                    self._serialize_datetime(new_last_attempt_at),
                    now_str,
                    row[0],
                ),
            )
            await conn.commit()

            # Create and return the updated task
            task: Task = {
                "id": row[0],
                "func_path": row[1],
                "args": self._deserialize_json(row[2]),
                "kwargs": self._deserialize_json(row[3]),
                "status": TaskStatus.RUNNING,
                "schedule": schedule,
                "max_retries": int(row[7]) if row[7] is not None else 0,
                "timeout": row[8],
                "attempts": new_attempts,
                "created_at": self._deserialize_datetime(row[10]),
                "updated_at": self._deserialize_datetime(now_str),
                "last_attempt_at": new_last_attempt_at,
            }

            # Add error field if present
            if len(row) > 13 and row[13] is not None:
                from ..serialization import deserialize_task_error

                task["error"] = deserialize_task_error(self._deserialize_json(row[13]))

            # Convert row to Task
            schedule = self._deserialize_json(row[5])
            eta = schedule.get("eta")
            if eta:
                schedule["eta"] = self._deserialize_datetime(eta)

            # Handle interval deserialization
            interval = schedule.get("interval")
            if (
                interval
                and isinstance(interval, dict)
                and interval.get("type") == "timedelta"
            ):
                from ..serialization import deserialize_timedelta

                schedule["interval"] = deserialize_timedelta(interval)

            task: Task = {
                "id": row[0],
                "func_path": row[1],
                "args": self._deserialize_json(row[2]),
                "kwargs": self._deserialize_json(row[3]),
                "status": TaskStatus(row[4]),
                "schedule": schedule,
                "max_retries": int(row[7]) if row[7] is not None else 0,
                "timeout": row[8],
                "attempts": int(row[9]) if row[9] is not None else 0,
                "created_at": self._deserialize_datetime(row[10]),
                "updated_at": self._deserialize_datetime(row[11]),
                "last_attempt_at": self._deserialize_datetime(row[12]),
            }

            # Add error field if present
            if len(row) > 13 and row[13] is not None:
                from ..serialization import deserialize_task_error

                task["error"] = deserialize_task_error(self._deserialize_json(row[13]))

            # Update attempts and last_attempt_at for RUNNING status
            # Don't increment attempts if this is a retry (attempts > 0)
            current_attempts = task.get("attempts", 0)
            print(
                f"DEBUG: In dequeue, task_id={task['id']}, current_attempts={current_attempts}"
            )
            if current_attempts > 0:
                # For retry tasks, just update timestamp without incrementing attempts
                # The attempts count was already incremented by mark_failed
                print("DEBUG: Using retry branch (no increment)")
                updated_task = task.copy()
                updated_task["status"] = TaskStatus.RUNNING
                updated_task["last_attempt_at"] = datetime.now(timezone.utc)
                updated_task["updated_at"] = datetime.now(timezone.utc)
            else:
                # For new tasks, use normal transition_status (increments attempts)
                print("DEBUG: Using new task branch (with increment)")
                updated_task = transition_status(task, TaskStatus.RUNNING)
            print(f"DEBUG: Final updated_task['attempts']={updated_task['attempts']}")

            # Update the task in database with new attempts/timestamp
            await conn.execute(
                """
                UPDATE tasks 
                SET attempts = ?, last_attempt_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (
                    updated_task["attempts"],
                    self._serialize_datetime(updated_task["last_attempt_at"]),
                    self._serialize_datetime(updated_task["updated_at"]),
                    task["id"],
                ),
            )
            await conn.commit()

            return updated_task

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to dequeue task: {e}")

    async def mark_running(self, task_id: str) -> None:
        """Update task status to RUNNING and update timestamps."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = self._serialize_datetime(now)

        try:
            cursor = await conn.execute(
                """
                UPDATE tasks 
                SET status = 'RUNNING', updated_at = ?, last_attempt_at = ?, attempts = attempts + 1
                WHERE id = ?
            """,
                (now_str, now_str, task_id),
            )

            if cursor.rowcount == 0:
                raise NotFoundError(f"Task {task_id} not found")

            await conn.commit()

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to mark task {task_id} as running: {e}")

    async def mark_done(self, task_id: str, result: TaskResult) -> None:
        """Persist a successful result and update task status to SUCCESS."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = self._serialize_datetime(now)

        try:
            # Start transaction
            await conn.execute("BEGIN IMMEDIATE")

            # Insert result
            await conn.execute(
                """
                INSERT OR REPLACE INTO results (
                    task_id, status, result, error, finished_at, attempts, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result["task_id"],
                    result["status"].value,
                    self._serialize_json(result["result"])
                    if result["result"] is not None
                    else None,
                    result["error"],
                    self._serialize_datetime(result["finished_at"]),
                    result["attempts"],
                    self._serialize_datetime(result["last_attempt_at"]),
                ),
            )

            # Update task status
            cursor = await conn.execute(
                """
                UPDATE tasks 
                SET status = 'SUCCESS', updated_at = ?
                WHERE id = ?
            """,
                (now_str, task_id),
            )

            if cursor.rowcount == 0:
                await conn.rollback()
                raise NotFoundError(f"Task {task_id} not found")

            await conn.commit()

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to mark task {task_id} as done: {e}")

    async def mark_failed(self, task_id: str, error: str, will_retry: bool) -> None:
        """Record a failure and update task status appropriately."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = self._serialize_datetime(now)

        try:
            # Start transaction
            await conn.execute("BEGIN IMMEDIATE")

            # Get current task info for result
            cursor = await conn.execute(
                """
                SELECT attempts, last_attempt_at FROM tasks WHERE id = ?
            """,
                (task_id,),
            )

            row = await cursor.fetchone()
            if row is None:
                await conn.rollback()
                raise NotFoundError(f"Task {task_id} not found")

            current_attempts = row[0] if row[0] is not None else 0
            attempts = current_attempts + 1  # Increment for this attempt
            print()
            last_attempt_at = now

            # Create failure result
            from ..models import create_failure_result

            failure_result = create_failure_result(
                task_id=task_id,
                error=error,
                attempts=attempts,
                last_attempt_at=last_attempt_at,
            )

            # Insert result
            await conn.execute(
                """
                INSERT OR REPLACE INTO results (
                    task_id, status, result, error, finished_at, attempts, last_attempt_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    failure_result["task_id"],
                    failure_result["status"].value,
                    self._serialize_json(failure_result["result"])
                    if failure_result["result"] is not None
                    else None,
                    failure_result["error"],
                    self._serialize_datetime(failure_result["finished_at"]),
                    failure_result["attempts"],
                    self._serialize_datetime(failure_result["last_attempt_at"]),
                ),
            )

            # Update task status
            new_status = "PENDING" if will_retry else "FAILED"
            cursor = await conn.execute(
                """
                UPDATE tasks 
                SET status = ?, updated_at = ?, attempts = ?, last_attempt_at = ?
                WHERE id = ?
            """,
                (new_status, now_str, attempts, now_str, task_id),
            )

            if cursor.rowcount == 0:
                await conn.rollback()
                raise NotFoundError(f"Task {task_id} not found")

            await conn.commit()

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to mark task {task_id} as failed: {e}")

    async def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve a task result by ID."""
        conn = await self._get_connection()

        try:
            cursor = await conn.execute(
                """
                SELECT task_id, status, result, error, finished_at, attempts, last_attempt_at
                FROM results 
                WHERE task_id = ?
            """,
                (task_id,),
            )

            row = await cursor.fetchone()
            if row is None:
                return None

            result: TaskResult = {
                "task_id": row[0],
                "status": TaskStatus(row[1]),
                "result": self._deserialize_json(row[2])
                if row[2] is not None
                else None,
                "error": row[3],
                "finished_at": self._deserialize_datetime(row[4]),
                "attempts": row[5],
                "last_attempt_at": self._deserialize_datetime(row[6]),
            }
            return result

        except Exception as e:
            raise StorageError(f"Failed to read result for task {task_id}: {e}")

    async def purge_results(self, older_than: datetime) -> int:
        """Remove old results based on age."""
        conn = await self._get_connection()
        cutoff_str = self._serialize_datetime(older_than)

        try:
            cursor = await conn.execute(
                """
                DELETE FROM results 
                WHERE finished_at < ?
            """,
                (cutoff_str,),
            )

            count = cursor.rowcount
            await conn.commit()
            return count

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to purge results: {e}")

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID from SQLite database."""
        conn = await self._get_connection()

        try:
            cursor = await conn.execute(
                """
                    SELECT id, func_path, args, kwargs, status, schedule, eta,
                           max_retries, timeout, attempts, created_at, updated_at, last_attempt_at, error
                    FROM tasks 
                    WHERE id = ?
                """,
                (task_id,),
            )

            row = await cursor.fetchone()
            if row is None:
                return None

            # Convert row to Task
            schedule = self._deserialize_json(row[5])
            eta = schedule.get("eta")
            if eta:
                schedule["eta"] = self._deserialize_datetime(eta)

            # Handle interval deserialization
            interval = schedule.get("interval")
            if (
                interval
                and isinstance(interval, dict)
                and interval.get("type") == "timedelta"
            ):
                from ..serialization import deserialize_timedelta

                schedule["interval"] = deserialize_timedelta(interval)

            task: Task = {
                "id": row[0],
                "func_path": row[1],
                "args": self._deserialize_json(row[2]),
                "kwargs": self._deserialize_json(row[3]),
                "status": TaskStatus(row[4]),
                "schedule": schedule,
                "max_retries": int(row[7]) if row[7] is not None else 0,
                "timeout": row[8],
                "attempts": int(row[9]) if row[9] is not None else 0,
                "created_at": self._deserialize_datetime(row[10]),
                "updated_at": self._deserialize_datetime(row[11]),
                "last_attempt_at": self._deserialize_datetime(row[12]),
            }

            # Add error field if present
            if len(row) > 13 and row[13] is not None:
                from ..serialization import deserialize_task_error

                task["error"] = deserialize_task_error(self._deserialize_json(row[13]))

            return task

        except Exception as e:
            raise StorageError(f"Failed to retrieve task {task_id}: {e}")

    async def reschedule(self, task_id: str, new_eta: datetime) -> None:
        """Update a task's eta for future execution."""
        conn = await self._get_connection()
        now = datetime.now(timezone.utc)
        now_str = self._serialize_datetime(now)
        new_eta_str = self._serialize_datetime(new_eta)

        try:
            # Get current task and schedule
            cursor = await conn.execute(
                """
                SELECT schedule FROM tasks WHERE id = ?
            """,
                (task_id,),
            )

            row = await cursor.fetchone()
            if row is None:
                raise NotFoundError(f"Task {task_id} not found")

            # Update schedule with new eta
            schedule = self._deserialize_json(row[0])
            schedule["eta"] = self._serialize_datetime(new_eta)
            updated_schedule_json = self._serialize_json(schedule)

            # Update task with new eta and PENDING status
            cursor = await conn.execute(
                """
                UPDATE tasks 
                SET status = 'PENDING', schedule = ?, updated_at = ?, eta = ?
                WHERE id = ?
            """,
                (updated_schedule_json, now_str, new_eta_str, task_id),
            )

            if cursor.rowcount == 0:
                raise NotFoundError(f"Task {task_id} not found")

            await conn.commit()

        except Exception as e:
            await conn.rollback()
            raise StorageError(f"Failed to reschedule task {task_id}: {e}")

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
