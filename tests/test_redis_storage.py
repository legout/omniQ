import asyncio
import time

import pytest

from omniq import OmniQ
from omniq.models import Schedule, Task, TaskResult
from omniq.serialization import default_serializer
from tests.helpers import sync_add

# Skip these tests if the redis library is not available
pytest.importorskip("redis")


# --- Fixtures ---


@pytest.fixture
def redis_omniq():
    """Provides an OmniQ instance with Redis storage (assumes a Redis server is running)."""
    # In a real test environment, you might use a testcontainer or a mock.
    # For now, we assume a Redis server is available at the default URL.
    try:
        return OmniQ(
            task_queue_url="redis://localhost:6379/0",
            result_storage_url="redis://localhost:6379/0",
            schedule_storage_url="redis://localhost:6379/0",
        )
    except ConnectionRefusedError:
        pytest.skip("Redis server not available. Skipping Redis storage tests.")


@pytest.fixture
async def clean_redis(redis_omniq):
    """Clean up any existing data in the Redis database before and after the test."""
    # It's better to create a new connection for cleanup to avoid interfering
    # with the one used by the instance under test.
    import redis.asyncio as redis
    redis_conn = redis.from_url("redis://localhost:6379/0")
    await redis_conn.flushdb()  # Clear the database
    yield
    await redis_conn.flushdb()  # Clear again after the test


# --- Task Queue Tests ---


@pytest.mark.asyncio
async def test_redis_enqueue_dequeue(redis_omniq: OmniQ, clean_redis):
    """Test enqueueing and dequeuing a task."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(3, 4), queue="redis_queue")
        task_id = await redis_omniq.task_queue.enqueue(task)

        dequeued_task = await redis_omniq.task_queue.dequeue(queues=["redis_queue"])
        assert dequeued_task is not None
        assert dequeued_task.id == task.id
        assert dequeued_task.func == task.func


@pytest.mark.asyncio
async def test_redis_ack(redis_omniq: OmniQ, clean_redis):
    """Test acknowledging a task."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(5, 6), queue="ack_queue")
        await redis_omniq.task_queue.enqueue(task)
        dequeued_task = await redis_omniq.task_queue.dequeue(queues=["ack_queue"])
        assert dequeued_task is not None

        await redis_omniq.task_queue.ack(dequeued_task)
        # The task should be removed from both the processing queue and the task data
        assert await redis_omniq.task_queue.get_task(dequeued_task.id) is None
        # Verify that it's not still in the processing list (implementation detail)
        processing_key = redis_omniq.task_queue._get_processing_key("ack_queue")
        assert await redis_omniq.task_queue.redis.llen(processing_key) == 0


@pytest.mark.asyncio
async def test_redis_nack_requeue(redis_omniq: OmniQ, clean_redis):
    """Test negatively acknowledging a task and requeuing it."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(7, 8), queue="nack_queue")
        await redis_omniq.task_queue.enqueue(task)
        dequeued_task = await redis_omniq.task_queue.dequeue(queues=["nack_queue"])
        assert dequeued_task is not None

        await redis_omniq.task_queue.nack(dequeued_task, requeue=True)
        # The task should be back in the main queue
        requeued_task = await redis_omniq.task_queue.dequeue(queues=["nack_queue"])
        assert requeued_task is not None
        assert requeued_task.id == task.id


@pytest.mark.asyncio
async def test_redis_nack_fail(redis_omniq: OmniQ, clean_redis):
    """Test negatively acknowledging a task without requeuing (failure)."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(9, 10), queue="fail_queue")
        await redis_omniq.task_queue.enqueue(task)
        dequeued_task = await redis_omniq.task_queue.dequeue(queues=["fail_queue"])
        assert dequeued_task is not None

        await redis_omniq.task_queue.nack(dequeued_task, requeue=False)
        # The task should be removed (similar to ack for this implementation)
        assert await redis_omniq.task_queue.get_task(dequeued_task.id) is None


@pytest.mark.asyncio
async def test_redis_dequeue_timeout(redis_omniq: OmniQ, clean_redis):
    """Test dequeue with a timeout."""
    async with redis_omniq:
        start_time = time.monotonic()
        result = await redis_omniq.task_queue.dequeue(queues=["nonexistent_queue"], timeout=0.2)
        duration = time.monotonic() - start_time
        assert result is None
        assert duration >= 0.2


# --- Result Storage Tests ---


@pytest.mark.asyncio
async def test_redis_result_store_get_delete(redis_omniq: OmniQ, clean_redis):
    """Test storing, retrieving, and deleting a result."""
    async with redis_omniq:
        result = TaskResult(
            task_id="result_123",
            status="SUCCESS",
            result=default_serializer.serialize(11),
            started_at=time.time(),
            worker_id="test_worker",
        )
        await redis_omniq.result_storage.store(result)

        retrieved = await redis_omniq.result_storage.get("result_123")
        assert retrieved is not None
        assert retrieved.task_id == "result_123"
        assert retrieved.status == "SUCCESS"
        assert default_serializer.deserialize(retrieved.result) == 11

        await redis_omniq.result_storage.delete("result_123")
        assert await redis_omniq.result_storage.get("result_123") is None


# --- Schedule Storage Tests ---


@pytest.mark.asyncio
async def test_redis_schedule_add_get(redis_omniq: OmniQ, clean_redis):
    """Test adding and retrieving a schedule."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(1, 1))
        schedule = Schedule(task=task, interval=60)
        schedule_id = await redis_omniq.schedule_storage.add_schedule(schedule)
        assert schedule_id == schedule.id

        retrieved = await redis_omniq.schedule_storage.get_schedule(schedule_id)
        assert retrieved is not None
        assert retrieved.id == schedule.id
        assert retrieved.interval == 60
        assert retrieved.task.func == task.func


@pytest.mark.asyncio
async def test_redis_schedule_list(redis_omniq: OmniQ, clean_redis):
    """Test listing all schedules."""
    async with redis_omniq:
        # Add two schedules
        task1 = Task(func=sync_add, args=(1, 1))
        schedule1 = Schedule(task=task1, interval=60)
        await redis_omniq.schedule_storage.add_schedule(schedule1)

        task2 = Task(func=sync_add, args=(2, 2))
        schedule2 = Schedule(task=task2, cron="* * * * *")
        await redis_omniq.schedule_storage.add_schedule(schedule2)

        schedules = await redis_omniq.schedule_storage.list_schedules()
        assert len(schedules) == 2
        schedule_ids = {s.id for s in schedules}
        assert {schedule1.id, schedule2.id} == schedule_ids


@pytest.mark.asyncio
async def test_redis_schedule_delete(redis_omniq: OmniQ, clean_redis):
    """Test deleting a schedule."""
    async with redis_omniq:
        task = Task(func=sync_add, args=(1, 1))
        schedule = Schedule(task=task, interval=60)
        schedule_id = await redis_omniq.schedule_storage.add_schedule(schedule)

        await redis_omniq.schedule_storage.delete_schedule(schedule_id)

        assert await redis_omniq.schedule_storage.get_schedule(schedule_id) is None


@pytest.mark.asyncio
async def test_redis_concurrent_dequeue(redis_omniq: OmniQ, clean_redis):
    """Verify that concurrent dequeues are atomic and don't have race conditions."""
    async with redis_omniq:
        num_tasks = 50
        queue_name = "concurrent_redis_queue"

        # 1. Enqueue a batch of tasks
        enqueued_ids = set()
        for i in range(num_tasks):
            task = Task(func=sync_add, args=(i, i), queue=queue_name)
            await redis_omniq.task_queue.enqueue(task)
            enqueued_ids.add(task.id)

        # 2. Create concurrent "workers" to dequeue
        num_workers = 5
        dequeued_ids_list = []  # A list to store all dequeued IDs

        async def worker():
            """A simple worker that dequeues tasks and adds their IDs to a list."""
            while True:
                task = await redis_omniq.task_queue.dequeue([queue_name], timeout=0.5)
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