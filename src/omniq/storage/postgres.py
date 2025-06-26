import asyncio
import logging
import time
from typing import List, Optional

try:
    import asyncpg
except ImportError:
    asyncpg = None

from omniq.models import Schedule, Task, TaskResult
from omniq.serialization import default_serializer
from omniq.storage import BaseResultStorage, BaseScheduleStorage, BaseTaskQueue

logger = logging.getLogger(__name__)

# --- Schema Definitions ---

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_tasks (
    id VARCHAR(36) PRIMARY KEY,
    queue VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'waiting', 'processing', 'failed'
    data BYTEA NOT NULL, -- Serialized Task object
    created_at DOUBLE PRECISION NOT NULL,
    retries INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_delay DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    dependencies_left INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_omniq_tasks_queue_status ON omniq_tasks (queue, status);
"""

CREATE_RESULTS_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_results (
    task_id VARCHAR(36) PRIMARY KEY,
    data BYTEA NOT NULL, -- Serialized TaskResult object
    completed_at DOUBLE PRECISION NOT NULL,
    worker_id VARCHAR(255)
);
"""

CREATE_SCHEDULES_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_schedules (
    id VARCHAR(36) PRIMARY KEY,
    data BYTEA NOT NULL, -- Serialized Schedule object
    cron VARCHAR(255),
    interval DOUBLE PRECISION,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    last_run_at DOUBLE PRECISION,
    next_run_at DOUBLE PRECISION
);
"""

CREATE_DEPENDENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS omniq_dependencies (
    dependency_id VARCHAR(36) NOT NULL,
    dependent_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (dependency_id, dependent_id)
);
"""


class PostgresStorageMixin:
    """Common logic for PostgreSQL backends."""

    def __init__(self, url: str):
        if asyncpg is None:
            raise ImportError("Please install 'omniq[postgres]' to use the PostgreSQL backend.")
        self.url = url
        self._pool: Optional[asyncpg.Pool] = None

    async def _get_pool(self) -> asyncpg.Pool:
        """Get a database connection pool, creating it if it doesn't exist."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.url, min_size=1, max_size=10)
            async with self._pool.acquire() as conn:
                await conn.execute(CREATE_TASKS_TABLE)
                await conn.execute(CREATE_RESULTS_TABLE)
                await conn.execute(CREATE_SCHEDULES_TABLE)
                await conn.execute(CREATE_DEPENDENCIES_TABLE)
        return self._pool

    async def __aenter__(self):
        await self._get_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._pool:
            await self._pool.close()
            self._pool = None


class PostgresTaskQueue(PostgresStorageMixin, BaseTaskQueue):
    """A transactional task queue using PostgreSQL for storage."""

    async def enqueue(self, task: Task) -> str:
        pool = await self._get_pool()

        if task.dependencies:
            task.status = "waiting"
            task.dependencies_left = len(task.dependencies)
        else:
            task.status = "pending"
            task.dependencies_left = 0

        serialized_task = default_serializer.serialize(task)

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO omniq_tasks (id, queue, status, data, created_at, retries, max_retries, retry_delay, dependencies_left)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    task.id, task.queue, task.status, serialized_task, task.created_at,
                    task.retries, task.max_retries, task.retry_delay, task.dependencies_left
                )
                if task.dependencies:
                    await conn.executemany(
                        "INSERT INTO omniq_dependencies (dependency_id, dependent_id) VALUES ($1, $2)",
                        [(dep_id, task.id) for dep_id in task.dependencies]
                    )
        return task.id

    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        pool = await self._get_pool()
        start_time = asyncio.get_event_loop().time()

        while True:
            async with pool.acquire() as conn:
                # Use SELECT FOR UPDATE SKIP LOCKED to atomically get and lock a task
                # and then update its status.
                task_record = await conn.fetchrow(
                    """
                    UPDATE omniq_tasks
                    SET status = 'processing'
                    WHERE id = (
                        SELECT id
                        FROM omniq_tasks
                        WHERE queue = ANY($1::text[]) AND status = 'pending'
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING data;
                    """,
                    queues,
                )

                if task_record:
                    return default_serializer.deserialize(task_record["data"], target_type=Task)

            if timeout == 0 or (asyncio.get_event_loop().time() - start_time) >= timeout:
                return None
            await asyncio.sleep(0.1)  # Polling delay

    async def get_task(self, task_id: str) -> Optional[Task]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            record = await conn.fetchrow("SELECT data FROM omniq_tasks WHERE id = $1", task_id)
            if record:
                return default_serializer.deserialize(record["data"], target_type=Task)
        return None

    async def ack(self, task: Task) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Find tasks that depend on the completed task
                dependent_records = await conn.fetch(
                    "SELECT dependent_id FROM omniq_dependencies WHERE dependency_id = $1", task.id
                )
                dependent_ids = [row['dependent_id'] for row in dependent_records]

                # For each dependent, decrement its counter
                for dep_id in dependent_ids:
                    # Atomically decrement and check
                    new_count = await conn.fetchval(
                        "UPDATE omniq_tasks SET dependencies_left = dependencies_left - 1 WHERE id = $1 RETURNING dependencies_left",
                        dep_id
                    )
                    if new_count is not None and new_count <= 0:
                        await conn.execute(
                            "UPDATE omniq_tasks SET status = 'pending' WHERE id = $1", dep_id
                        )

                # Clean up dependencies
                await conn.execute("DELETE FROM omniq_dependencies WHERE dependency_id = $1", task.id)

                # Finally, delete the completed task
                await conn.execute("DELETE FROM omniq_tasks WHERE id = $1", task.id)

    async def nack(self, task: Task, requeue: bool = True) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if requeue:
                # Re-serialize the task as its retry count might have changed
                new_data = default_serializer.serialize(task)
                await conn.execute(
                    "UPDATE omniq_tasks SET status = 'pending', data = $1 WHERE id = $2",
                    new_data,
                    task.id,
                )
            else:
                await conn.execute(
                    "UPDATE omniq_tasks SET status = 'failed' WHERE id = $1", task.id
                )


class PostgresResultStorage(PostgresStorageMixin, BaseResultStorage):
    """Result storage using PostgreSQL."""

    async def store(self, result: TaskResult) -> None:
        pool = await self._get_pool()
        serialized_result = default_serializer.serialize(result)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO omniq_results (task_id, data, completed_at, worker_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (task_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    completed_at = EXCLUDED.completed_at,
                    worker_id = EXCLUDED.worker_id;
                """,
                result.task_id,
                serialized_result,
                result.completed_at,
                result.worker_id,
            )

    async def get(self, task_id: str) -> Optional[TaskResult]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            record = await conn.fetchrow("SELECT data FROM omniq_results WHERE task_id = $1", task_id)
            if record:
                return default_serializer.deserialize(record["data"], target_type=TaskResult)
        return None

    async def delete(self, task_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM omniq_results WHERE task_id = $1", task_id)

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT data FROM omniq_tasks WHERE status IN ('pending', 'waiting')"
            params = []
            if queue:
                query += " AND queue = $1"
                params.append(queue)
            query += " ORDER BY created_at LIMIT $2"
            params.append(limit)
            records = await conn.fetch(query, *params)
            return [default_serializer.deserialize(r["data"], target_type=Task) for r in records]

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            query = "SELECT data FROM omniq_tasks WHERE status = 'failed'"
            params = []
            if queue:
                query += " AND queue = $1"
                params.append(queue)
            query += " ORDER BY created_at DESC LIMIT $2"
            params.append(limit)
            records = await conn.fetch(query, *params)
            return [default_serializer.deserialize(r["data"], target_type=Task) for r in records]

    async def _update_pause_status(self, schedule_id: str, is_paused: bool) -> Optional[Schedule]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Fetch, update, and re-serialize the schedule
            record = await conn.fetchrow("SELECT data FROM omniq_schedules WHERE id = $1 FOR UPDATE", schedule_id)
            if not record:
                return None
            schedule = default_serializer.deserialize(record["data"], target_type=Schedule)
            schedule.is_paused = is_paused
            updated_data = default_serializer.serialize(schedule)

            await conn.execute(
                "UPDATE omniq_schedules SET is_paused = $1, data = $2 WHERE id = $3",
                is_paused,
                updated_data,
                schedule.id,
            )
            return schedule

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, True)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, False)

    async def list_recent_results(self, limit: int) -> List[TaskResult]:
        """List the most recent task results."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT data FROM omniq_results ORDER BY completed_at DESC LIMIT $1", limit
            )
            return [
                default_serializer.deserialize(r["data"], target_type=TaskResult) for r in records
            ]


class PostgresScheduleStorage(PostgresStorageMixin, BaseScheduleStorage):
    """Schedule storage using PostgreSQL."""

    async def add_schedule(self, schedule: Schedule) -> str:
        pool = await self._get_pool()
        serialized_schedule = default_serializer.serialize(schedule)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO omniq_schedules (id, data, cron, interval, is_paused, last_run_at, next_run_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (id) DO UPDATE SET
                    data = EXCLUDED.data,
                    cron = EXCLUDED.cron,
                    interval = EXCLUDED.interval,
                    is_paused = EXCLUDED.is_paused,
                    last_run_at = EXCLUDED.last_run_at,
                    next_run_at = EXCLUDED.next_run_at;
                """,
                schedule.id,
                serialized_schedule,
                schedule.cron,
                schedule.interval,
                schedule.is_paused,
                schedule.last_run_at,
                schedule.next_run_at,
            )
        return schedule.id

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            record = await conn.fetchrow("SELECT data FROM omniq_schedules WHERE id = $1", schedule_id)
            if record:
                return default_serializer.deserialize(record["data"], target_type=Schedule)
        return None

    async def list_schedules(self) -> List[Schedule]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch("SELECT data FROM omniq_schedules")
            return [default_serializer.deserialize(r["data"], target_type=Schedule) for r in records]

    async def delete_schedule(self, schedule_id: str) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM omniq_schedules WHERE id = $1", schedule_id)

    async def _update_pause_status(self, schedule_id: str, is_paused: bool) -> Optional[Schedule]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Fetch, update, and re-serialize the schedule
            record = await conn.fetchrow("SELECT data FROM omniq_schedules WHERE id = $1 FOR UPDATE", schedule_id)
            if not record:
                return None
            schedule = default_serializer.deserialize(record["data"], target_type=Schedule)
            schedule.is_paused = is_paused
            updated_data = default_serializer.serialize(schedule)

            await conn.execute(
                "UPDATE omniq_schedules SET is_paused = $1, data = $2 WHERE id = $3",
                is_paused,
                updated_data,
                schedule.id,
            )
            return schedule

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, True)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, False)