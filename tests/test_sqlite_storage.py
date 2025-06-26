import asyncio
import os
import shutil
import time

import pytest

from omniq import OmniQ
from omniq.models import Task, TaskResult
from omniq.serialization import default_serializer
from tests.helpers import sync_add

# Mark all tests in this module to be skipped if aiosqlite is not installed
pytest.importorskip("aiosqlite")


# --- Fixtures ---


@pytest.fixture
def temp_dir():
    """Create and clean up a temporary directory for file-based SQLite testing."""
    path = "test_sqlite_storage_dir"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    yield path
    shutil.rmtree(path)


@pytest.fixture
def sqlite_file_omniq(temp_dir):
    """Provides an OmniQ instance with a file-based SQLite backend."""
    db_path = os.path.join(temp_dir, "omniq.db")
    return OmniQ(
        task_queue_url=f"sqlite://{db_path}",
        result_storage_url=f"sqlite://{db_path}",
    )


@pytest.fixture
def sqlite_memory_omniq():
    """Provides an OmniQ instance with an in-memory SQLite backend."""
    return OmniQ(
        task_queue_url="sqlite://:memory:",
        result_storage_url="sqlite://:memory:",
    )


@pytest.fixture(params=["sqlite_file_omniq", "sqlite_memory_omniq"])
def omniq_sqlite(request):
    """Parametrized fixture to run tests against both file and memory backends."""
    return request.getfixturevalue(request.param)


# --- Task Queue Tests ---


@pytest.mark.asyncio
async def test_sqlite_enqueue_dequeue(omniq_sqlite: OmniQ):
    """Test basic enqueue and dequeue functionality."""
    async with omniq_sqlite:
        task = Task(func=sync_add, args=(1, 2), queue="q1")
        task_id = await omniq_sqlite.task_queue.enqueue(task)
        assert task_id == task.id

        dequeued_task = await omniq_sqlite.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        # The dequeued task should now be in 'processing' state and not available
        assert await omniq_sqlite.task_queue.dequeue(queues=["q1"], timeout=0) is None


@pytest.mark.asyncio
async def test_sqlite_ack(omniq_sqlite: OmniQ):
    """Test that acknowledging a task removes it."""
    async with omniq_sqlite:
        task_id = await omniq_sqlite.enqueue(sync_add, 1, 2, queue="q1")
        dequeued_task = await omniq_sqlite.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None
        assert dequeued_task.id == task_id

        await omniq_sqlite.task_queue.ack(dequeued_task)

        # The task should be gone completely
        assert await omniq_sqlite.task_queue.get_task(task_id) is None


@pytest.mark.asyncio
async def test_sqlite_nack_requeue(omniq_sqlite: OmniQ):
    """Test that nacking with requeue makes the task available again."""
    async with omniq_sqlite:
        task = Task(func=sync_add, args=(1, 2), queue="q1")
        await omniq_sqlite.task_queue.enqueue(task)

        dequeued_task = await omniq_sqlite.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None

        # Nack it to put it back in the queue
        await omniq_sqlite.task_queue.nack(dequeued_task, requeue=True)

        # It should be available again
        requeued_task = await omniq_sqlite.task_queue.dequeue(queues=["q1"])
        assert requeued_task is not None
        assert requeued_task.id == task.id


@pytest.mark.asyncio
async def test_sqlite_nack_fail(omniq_sqlite: OmniQ):
    """Test that nacking without requeue marks the task as failed."""
    async with omniq_sqlite:
        task_id = await omniq_sqlite.enqueue(sync_add, 1, 2, queue="q1")
        dequeued_task = await omniq_sqlite.task_queue.dequeue(queues=["q1"])
        assert dequeued_task is not None

        await omniq_sqlite.task_queue.nack(dequeued_task, requeue=False)

        # It should NOT be available for dequeuing
        assert await omniq_sqlite.task_queue.dequeue(queues=["q1"], timeout=0) is None

        # But it should still exist in the table with a 'failed' status
        failed_task_record = await omniq_sqlite.task_queue.get_task(task_id)
        assert failed_task_record is not None


@pytest.mark.asyncio
async def test_sqlite_dequeue_timeout(omniq_sqlite: OmniQ):
    """Test that dequeue times out correctly."""
    async with omniq_sqlite:
        start_time = asyncio.get_event_loop().time()
        result = await omniq_sqlite.task_queue.dequeue(queues=["non_existent"], timeout=0.1)
        duration = asyncio.get_event_loop().time() - start_time
        assert result is None
        assert duration >= 0.1


@pytest.mark.asyncio
async def test_sqlite_concurrent_dequeue(omniq_sqlite: OmniQ):
    """Verify that concurrent dequeues are atomic and don't have race conditions."""
    async with omniq_sqlite:
        num_tasks = 50
        queue_name = "concurrent_queue"

        # 1. Enqueue a batch of tasks
        enqueued_ids = set()
        for i in range(num_tasks):
            task = Task(func=sync_add, args=(i, i), queue=queue_name)
            await omniq_sqlite.task_queue.enqueue(task)
            enqueued_ids.add(task.id)

        # 2. Create concurrent "workers" to dequeue
        num_workers = 5
        dequeued_ids_list = []  # A list to store all dequeued IDs

        async def worker():
            """A simple worker that dequeues tasks and adds their IDs to a list."""
            while True:
                task = await omniq_sqlite.task_queue.dequeue([queue_name], timeout=0.5)
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
async def test_sqlite_result_store_get_delete(omniq_sqlite: OmniQ):
    """Test storing, retrieving, and deleting a result."""
    async with omniq_sqlite:
        result = TaskResult(
            task_id="res-123",
            status="SUCCESS",
            result=default_serializer.serialize("all good"),
            started_at=time.time(),
            worker_id="worker-1",
        )
        await omniq_sqlite.result_storage.store(result)

        retrieved = await omniq_sqlite.result_storage.get("res-123")
        assert retrieved is not None
        assert retrieved.task_id == "res-123"
        assert retrieved.status == "SUCCESS"
        assert default_serializer.deserialize(retrieved.result) == "all good"

        await omniq_sqlite.result_storage.delete("res-123")
        assert await omniq_sqlite.result_storage.get("res-123") is None