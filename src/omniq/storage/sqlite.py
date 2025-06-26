import asyncio
from pathlib import Path
from typing import List, Optional

import aiosqlite

from omniq.models import Task, TaskResult
from omniq.models import Schedule
from omniq.serialization import default_serializer
from omniq.storage import BaseResultStorage, BaseScheduleStorage, BaseTaskQueue

# --- Schema Definitions ---

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_tasks (
    id TEXT PRIMARY KEY,
    queue TEXT NOT NULL,
    status TEXT NOT NULL, -- pending, waiting, processing, failed
    data BLOB NOT NULL,
    created_at REAL NOT NULL,
    dependencies_left INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_results (
    task_id TEXT PRIMARY KEY,
    data BLOB NOT NULL,
    completed_at REAL NOT NULL
);
"""

CREATE_SCHEDULES_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_schedules (
    id TEXT PRIMARY KEY,
    data BLOB NOT NULL,
    cron TEXT,
    interval REAL,
    is_paused INTEGER NOT NULL DEFAULT 0,
    next_run_at REAL
);
"""

CREATE_DEPENDENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_dependencies (
    dependency_id TEXT NOT NULL,
    dependent_id TEXT NOT NULL,
    PRIMARY KEY (dependency_id, dependent_id)
);
"""

CREATE_QUEUE_INDEX = "CREATE INDEX IF NOT EXISTS idx_omniq_tasks_queue_status ON omniq_tasks (queue, status);"


class SqliteStorageMixin:
    """Common logic for SQLite backends."""

    def __init__(self, url: str):
        db_path = url.removeprefix("sqlite://")
        # An in-memory database is specified by ":memory:" or an empty path
        self.is_memory_db = not db_path or db_path == ":memory:"
        self.db_path = ":memory:" if self.is_memory_db else str(Path(db_path).resolve())
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def _get_db(self) -> aiosqlite.Connection:
        """Get a database connection, creating it if it doesn't exist."""
        async with self._lock:
            if self._db is None:
                if not self.is_memory_db:
                    Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

                self._db = await aiosqlite.connect(self.db_path)
                # WAL mode is good for concurrency but persists only for file-based dbs
                if not self.is_memory_db:
                    await self._db.execute("PRAGMA journal_mode=WAL;")

                await self._db.execute(CREATE_TASKS_TABLE)
                await self._db.execute(CREATE_RESULTS_TABLE)
                await self._db.execute(CREATE_SCHEDULES_TABLE)
                await self._db.execute(CREATE_DEPENDENCIES_TABLE)
                await self._db.execute(CREATE_QUEUE_INDEX)
                await self._db.commit()
        return self._db

    async def __aenter__(self):
        await self._get_db()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._db:
            await self._db.close()
            self._db = None


class SqliteTaskQueue(SqliteStorageMixin, BaseTaskQueue):
    """A transactional task queue using SQLite for storage."""

    async def enqueue(self, task: Task) -> str:
        db = await self._get_db()

        if task.dependencies:
            task.status = "waiting"
            task.dependencies_left = len(task.dependencies)
        else:
            task.status = "pending"
            task.dependencies_left = 0

        serialized_task = default_serializer.serialize(task)

        async with db as conn:  # transaction
            await conn.execute(
                "INSERT INTO omniq_tasks (id, queue, status, data, created_at, dependencies_left) VALUES (?, ?, ?, ?, ?, ?)",
                (task.id, task.queue, task.status, serialized_task, task.created_at, task.dependencies_left),
            )
            if task.dependencies:
                await conn.executemany(
                    "INSERT INTO omniq_dependencies (dependency_id, dependent_id) VALUES (?, ?)",
                    [(dep_id, task.id) for dep_id in task.dependencies]
                )
        return task.id

    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        db = await self._get_db()
        placeholders = ",".join("?" for _ in queues)
        query = f"""
            SELECT id, data FROM omniq_tasks
            WHERE queue IN ({placeholders}) AND status = 'pending'
            ORDER BY created_at
            LIMIT 1
        """

        start_time = asyncio.get_event_loop().time()
        while True:
            # Using the connection as a context manager handles transactions.
            async with db as conn:
                cursor = await conn.execute(query, queues)
                row = await cursor.fetchone()
                if row:
                    task_id, data = row
                    await conn.execute(
                        "UPDATE omniq_tasks SET status = 'processing' WHERE id = ?", (task_id,)
                    )
                    return default_serializer.deserialize(data, target_type=Task)

            if timeout == 0 or (asyncio.get_event_loop().time() - start_time) >= timeout:
                return None
            await asyncio.sleep(0.1)  # Polling delay

    async def get_task(self, task_id: str) -> Optional[Task]:
        db = await self._get_db()
        cursor = await db.execute("SELECT data FROM omniq_tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return default_serializer.deserialize(row[0], target_type=Task)
        return None

    async def ack(self, task: Task) -> None:
        db = await self._get_db()
        async with db as conn:  # transaction
            # Find tasks that depend on the completed task
            cursor = await conn.execute(
                "SELECT dependent_id FROM omniq_dependencies WHERE dependency_id = ?", (task.id,)
            )
            dependent_ids = [row[0] for row in await cursor.fetchall()]

            # For each dependent, decrement its counter
            for dep_id in dependent_ids:
                update_cursor = await conn.execute(
                    "UPDATE omniq_tasks SET dependencies_left = dependencies_left - 1 WHERE id = ? RETURNING dependencies_left",
                    (dep_id,)
                )
                result = await update_cursor.fetchone()
                if result and result[0] <= 0:
                    # If counter is zero, make the task pending
                    await conn.execute(
                        "UPDATE omniq_tasks SET status = 'pending' WHERE id = ?", (dep_id,)
                    )

            # Clean up dependencies and the completed task
            await conn.execute("DELETE FROM omniq_dependencies WHERE dependency_id = ?", (task.id,))
            await conn.execute("DELETE FROM omniq_tasks WHERE id = ?", (task.id,))

    async def nack(self, task: Task, requeue: bool = True) -> None:
        db = await self._get_db()
        if requeue:
            # The task object has been modified (e.g., retries incremented), so we re-serialize.
            new_data = default_serializer.serialize(task)
            await db.execute(
                "UPDATE omniq_tasks SET status = 'pending', data = ? WHERE id = ?",
                (new_data, task.id),
            )
        else:
            # Mark as failed and leave it in the table for inspection.
            # A separate cleanup process could remove old failed tasks.
            await db.execute(
                "UPDATE omniq_tasks SET status = 'failed' WHERE id = ?", (task.id,)
            )
        await db.commit()


class SqliteResultStorage(SqliteStorageMixin, BaseResultStorage):
    """Result storage using SQLite."""

    async def store(self, result: TaskResult) -> None:
        db = await self._get_db()
        serialized_result = default_serializer.serialize(result)
        await db.execute(
            "INSERT OR REPLACE INTO omniq_results (task_id, data, completed_at) VALUES (?, ?, ?)",
            (result.task_id, serialized_result, result.completed_at),
        )
        await db.commit()

    async def get(self, task_id: str) -> Optional[TaskResult]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT data FROM omniq_results WHERE task_id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return default_serializer.deserialize(row[0], target_type=TaskResult)
        return None

    async def delete(self, task_id: str) -> None:
        db = await self._get_db()
        await db.execute("DELETE FROM omniq_results WHERE task_id = ?", (task_id,))
        await db.commit()

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        db = await self._get_db()
        query = "SELECT data FROM omniq_tasks WHERE status IN ('pending', 'waiting')"
        params = []
        if queue:
            query += " AND queue = ?"
            params.append(queue)
        query += " ORDER BY created_at LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [default_serializer.deserialize(row[0], target_type=Task) for row in rows]

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        db = await self._get_db()
        query = "SELECT data FROM omniq_tasks WHERE status = 'failed'"
        params = []
        if queue:
            query += " AND queue = ?"
            params.append(queue)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [default_serializer.deserialize(row[0], target_type=Task) for row in rows]

    async def list_recent_results(self, limit: int) -> List[TaskResult]:
        """List the most recent task results."""
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT data FROM omniq_results ORDER BY completed_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [default_serializer.deserialize(row[0], target_type=TaskResult) for row in rows]


class SqliteScheduleStorage(SqliteStorageMixin, BaseScheduleStorage):
    """Schedule storage using SQLite."""

    async def add_schedule(self, schedule: Schedule) -> str:
        db = await self._get_db()
        serialized_schedule = default_serializer.serialize(schedule)
        await db.execute(
            """
            INSERT OR REPLACE INTO omniq_schedules
            (id, data, cron, interval, is_paused, next_run_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                schedule.id,
                serialized_schedule,
                schedule.cron,
                schedule.interval,
                int(schedule.is_paused),
                schedule.next_run_at,
            ),
        )
        await db.commit()
        return schedule.id

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT data FROM omniq_schedules WHERE id = ?", (schedule_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return default_serializer.deserialize(row[0], target_type=Schedule)
        return None

    async def list_schedules(self) -> List[Schedule]:
        db = await self._get_db()
        cursor = await db.execute("SELECT data FROM omniq_schedules")
        rows = await cursor.fetchall()
        return [default_serializer.deserialize(row[0], target_type=Schedule) for row in rows]

    async def delete_schedule(self, schedule_id: str) -> None:
        db = await self._get_db()
        await db.execute("DELETE FROM omniq_schedules WHERE id = ?", (schedule_id,))
        await db.commit()

    async def _update_pause_status(
        self, schedule_id: str, is_paused: bool
    ) -> Optional[Schedule]:
        db = await self._get_db()
        async with db as conn:  # transaction
            cursor = await conn.execute(
                "SELECT data FROM omniq_schedules WHERE id = ?", (schedule_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            schedule = default_serializer.deserialize(row[0], target_type=Schedule)
            schedule.is_paused = is_paused
            new_data = default_serializer.serialize(schedule)

            await conn.execute(
                "UPDATE omniq_schedules SET is_paused = ?, data = ? WHERE id = ?",
                (int(is_paused), new_data, schedule_id),
            )
        return schedule

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, True)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, False)

    async def _update_pause_status(
        self, schedule_id: str, is_paused: bool
    ) -> Optional[Schedule]:
        db = await self._get_db()
        async with db as conn:  # transaction
            cursor = await conn.execute(
                "SELECT data FROM omniq_schedules WHERE id = ?", (schedule_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None

            schedule = default_serializer.deserialize(row[0], target_type=Schedule)
            schedule.is_paused = is_paused
            new_data = default_serializer.serialize(schedule)

            await conn.execute(
                "UPDATE omniq_schedules SET is_paused = ?, data = ? WHERE id = ?",
                (int(is_paused), new_data, schedule_id),
            )
        return schedule

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, True)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, False)