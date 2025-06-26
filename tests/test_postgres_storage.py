import asyncio
import os
import time
import logging

import pytest

try:
    import asyncpg
except ImportError:
    asyncpg = None

from omniq import OmniQ
from omniq.models import Schedule, Task, TaskResult
from omniq.serialization import default_serializer
from tests.helpers import sync_add

# Skip all tests in this module if asyncpg is not installed
pytest.importorskip("asyncpg")

logger = logging.getLogger(__name__)

# --- Fixtures ---


@pytest.fixture(scope="module")
async def postgres_test_db():
    """
    Fixture to set up and tear down a test PostgreSQL database.
    Assumes a PostgreSQL server is running and accessible.
    Uses a separate database for testing to avoid conflicts.
    """
    # Get connection details from environment or default
    # Example: postgresql://user:password@localhost:5432/test_omniq
    db_url = os.environ.get("POSTGRES_TEST_URL", "postgresql://postgres:postgres@localhost:5432/test_omniq")

    # Parse the URL to get components for creating/dropping database
    parsed_url = asyncpg.connect_utils.parse_dsn(db_url)
    db_name = parsed_url.get("database", "test_omniq")
    # Connect to default 'postgres' database to manage test_db
    admin_url = db_url.replace(f"/{db_name}", "/postgres")

    conn = None
    try:
        conn = await asyncpg.connect(admin_url)
        # Drop and recreate the test database
        await conn.execute(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
        await conn.execute(f"CREATE DATABASE {db_name};")
        await conn.close()
        yield db_url  # Yield the connection string for the test database
    except Exception as e:
        pytest.fail(f"Could not connect to PostgreSQL or manage test database: {e}. "
                    "Ensure PostgreSQL is running and accessible, and user has privileges to create databases.")
    finally:
        if conn and not conn.is_closed():
            await conn.close()
        # Clean up: drop the test database after all tests in the module
        try:
            conn = await asyncpg.connect(admin_url)
            await conn.execute(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
        except Exception as e:
            logger.error(f"Error during PostgreSQL test database cleanup: {e}")
        finally:
            if conn and not conn.is_closed():
                await conn.close()


@pytest.fixture
async def omniq_postgres(postgres_test_db):
    """Provides an OmniQ instance with PostgreSQL storage."""
    omniq_instance = OmniQ(
        task_queue_url=postgres_test_db,
        result_storage_url=postgres_test_db,
        schedule_storage_url=postgres_test_db,
    )
    # Ensure tables are created and clean state for each test
    async with omniq_instance:
        # Truncate tables for each test to ensure isolation
        # This is faster than dropping/recreating for each test
        pool = await omniq_instance.task_queue._get_pool()  # Access internal pool
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE omniq_tasks, omniq_results, omniq_schedules RESTART IDENTITY;")
        yield omniq_instance
    # The __aexit__ of OmniQ will close the pool


# --- Task Queue Tests ---


@pytest.mark.asyncio
async def test_postgres_enqueue_dequeue(omniq_postgres: OmniQ):
    """Test basic enqueue and dequeue functionality."""
    async with omniq_postgres:
        task = Task(func=sync_add, args=(1, 2), queue="q1")
        task_id = await omniq_postgres.task_queue.enqueue(task)
        assert task_id == task.id

        dequeued_task = await omniq_postgres.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        # The dequeued task should now be in 'processing' state and not available
        assert await omniq_postgres.task_queue.dequeue(queues=["q1"], timeout=0) is None


@pytest.mark.asyncio
async def test_postgres_ack(omniq_postgres: OmniQ):
    """Test that acknowledging a task removes it."""
    async with omniq_postgres:
        task_id = await omniq_postgres.enqueue(sync_add, 1, 2, queue="q1")
        dequeued_task = await omniq_postgres.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None
        assert dequeued_task.id == task_id

        await omniq_postgres.task_queue.ack(dequeued_task)

        # The task should be gone completely
        assert await omniq_postgres.task_queue.get_task(task_id) is None


@pytest.mark.asyncio
async def test_postgres_nack_requeue(omniq_postgres: OmniQ):
    """Test that nacking with requeue makes the task available again."""
    async with omniq_postgres:
        task = Task(func=sync_add, args=(1, 2), queue="q1")
        await omniq_postgres.task_queue.enqueue(task)

        dequeued_task = await omniq_postgres.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None

        # Nack it to put it back in the queue
        await omniq_postgres.task_queue.nack(dequeued_task, requeue=True)

        # It should be available again
        requeued_task = await omniq_postgres.task_queue.dequeue(queues=["q1"])
        assert requeued_task is not None
        assert requeued_task.id == task.id


@pytest.mark.asyncio
async def test_postgres_nack_fail(omniq_postgres: OmniQ):
    """Test that nacking without requeue marks the task as failed."""
    async with omniq_postgres:
        task_id = await omniq_postgres.enqueue(sync_add, 1, 2, queue="q1")
        dequeued_task = await omniq_postgres.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None

        await omniq_postgres.task_queue.nack(dequeued_task, requeue=False)

        # It should NOT be available for dequeuing
        assert await omniq_postgres.task_queue.dequeue(queues=["q1"], timeout=0) is None

        # But it should still exist in the table with a 'failed' status
        failed_task_record = await omniq_postgres.task_queue.get_task(task_id)
        assert failed_task_record is not None


@pytest.mark.asyncio
async def test_postgres_dequeue_timeout(omniq_postgres: OmniQ):
    """Test that dequeue times out correctly."""
    async with omniq_postgres:
        start_time = asyncio.get_event_loop().time()
        result = await omniq_postgres.task_queue.dequeue(queues=["non_existent"], timeout=0.1)
        duration = asyncio.get_event_loop().time() - start_time
        assert result is None
        assert duration >= 0.1


@pytest.mark.asyncio
async def test_postgres_concurrent_dequeue(omniq_postgres: OmniQ):
    """Verify that concurrent dequeues are atomic and don't have race conditions."""
    async with omniq_postgres:
        num_tasks = 50
        queue_name = "concurrent_pg_queue"

        # 1. Enqueue a batch of tasks
        enqueued_ids = set()
        for i in range(num_tasks):
            task = Task(func=sync_add, args=(i, i), queue=queue_name)
            await omniq_postgres.task_queue.enqueue(task)
            enqueued_ids.add(task.id)

        # 2. Create concurrent "workers" to dequeue
        num_workers = 5
        dequeued_ids_list = []  # A list to store all dequeued IDs

        async def worker():
            """A simple worker that dequeues tasks and adds their IDs to a list."""
            while True:
                task = await omniq_postgres.task_queue.dequeue([queue_name], timeout=0.5)
                if task:
                    dequeued_ids_list.append(task.id)
                else:
                    break  # No more tasks

        # 3. Run workers concurrently
        worker_tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]
        await asyncio.gather(*worker_tasks)

        # 4. Assertions
        assert len(dequeued_ids_list) == num_tasks
        assert len(set(dequeued_ids_list)) == num_tasks, "A task was dequeued more than once"
        assert set(dequeued_ids_list) == enqueued_ids


# --- Result Storage Tests ---


@pytest.mark.asyncio
async def test_postgres_result_store_get_delete(omniq_postgres: OmniQ):
    """Test storing, retrieving, and deleting a result."""
    async with omniq_postgres:
        result = TaskResult(
            task_id="pg_res-123",
            status="SUCCESS",
            result=default_serializer.serialize("pg task completed successfully"),
            started_at=time.time(),
            worker_id="pg_worker-1",
        )
        await omniq_postgres.result_storage.store(result)

        retrieved = await omniq_postgres.result_storage.get("pg_res-123")
        assert retrieved is not None
        assert retrieved.task_id == "pg_res-123"
        assert retrieved.status == "SUCCESS"
        assert default_serializer.deserialize(retrieved.result) == "pg task completed successfully"

        await omniq_postgres.result_storage.delete("pg_res-123")
        assert await omniq_postgres.result_storage.get("pg_res-123") is None


# --- Schedule Storage Tests ---


@pytest.mark.asyncio
async def test_postgres_schedule_add_get_list_delete(omniq_postgres: OmniQ):
    """Test adding, getting, listing, and deleting schedules."""
    async with omniq_postgres:
        task = Task(func=sync_add, args=(1, 1))
        schedule1 = Schedule(task=task, interval=60)
        schedule2 = Schedule(task=task, cron="* * * * *")

        await omniq_postgres.schedule_storage.add_schedule(schedule1)
        await omniq_postgres.schedule_storage.add_schedule(schedule2)

        retrieved_schedule1 = await omniq_postgres.schedule_storage.get_schedule(schedule1.id)
        assert retrieved_schedule1 is not None
        assert retrieved_schedule1.id == schedule1.id
        assert retrieved_schedule1.interval == 60

        all_schedules = await omniq_postgres.schedule_storage.list_schedules()
        assert len(all_schedules) == 2
        assert {s.id for s in all_schedules} == {schedule1.id, schedule2.id}

        await omniq_postgres.schedule_storage.delete_schedule(schedule1.id)
        assert await omniq_postgres.schedule_storage.get_schedule(schedule1.id) is None
        assert len(await omniq_postgres.schedule_storage.list_schedules()) == 1


@pytest.mark.asyncio
async def test_postgres_schedule_pause_resume(omniq_postgres: OmniQ):
    """Test pausing and resuming a schedule."""
    async with omniq_postgres:
        task = Task(func=sync_add, args=(1, 1))
        schedule = Schedule(task=task, interval=60, is_paused=False)
        await omniq_postgres.schedule_storage.add_schedule(schedule)

        # Pause
        paused_schedule = await omniq_postgres.schedule_storage.pause_schedule(schedule.id)
        assert paused_schedule is not None
        assert paused_schedule.is_paused is True
        retrieved = await omniq_postgres.schedule_storage.get_schedule(schedule.id)
        assert retrieved.is_paused is True

        # Resume
        resumed_schedule = await omniq_postgres.schedule_storage.resume_schedule(schedule.id)
        assert resumed_schedule is not None
        assert resumed_schedule.is_paused is False
        retrieved = await omniq_postgres.schedule_storage.get_schedule(schedule.id)
        assert retrieved.is_paused is False