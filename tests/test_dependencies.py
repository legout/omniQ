import asyncio

import pytest

from omniq import OmniQ
from omniq.models import Task
from tests.helpers import sync_add

# --- Fixtures ---


@pytest.fixture
def omniq_memory():
    """Provides an OmniQ instance with in-memory storage."""
    return OmniQ(
        task_queue_url="memory://",
        result_storage_url="memory://",
    )


@pytest.fixture
async def omniq_sqlite(tmp_path):
    """Provides an OmniQ instance with a file-based SQLite backend."""
    db_path = tmp_path / "omniq_deps.db"
    omniq_instance = OmniQ(
        task_queue_url=f"sqlite://{db_path}",
        result_storage_url=f"sqlite://{db_path}",
    )
    async with omniq_instance:
        yield omniq_instance


@pytest.fixture
async def omniq_postgres(postgres_test_db):
    """Provides an OmniQ instance with PostgreSQL storage."""
    omniq_instance = OmniQ(
        task_queue_url=postgres_test_db,
        result_storage_url=postgres_test_db,
    )
    async with omniq_instance:
        pool = await omniq_instance.task_queue._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE omniq_tasks, omniq_results, omniq_schedules RESTART IDENTITY;")
        yield omniq_instance


@pytest.fixture(params=["omniq_memory", "omniq_sqlite", "omniq_postgres"])
async def omniq_backend(request):
    """Parametrized fixture to run dependency tests against all supported backends."""
    # We need to await the async fixtures
    if asyncio.iscoroutinefunction(request.getfixturevalue(request.param)):
        instance = await request.getfixturevalue(request.param)
    else:
        instance = request.getfixturevalue(request.param)
    yield instance


# --- Tests ---


@pytest.mark.asyncio
async def test_task_with_dependencies_waits(omniq_backend: OmniQ):
    """Test that a task with dependencies is not dequeued until they are met."""
    async with omniq_backend as omniq:
        # Enqueue two prerequisite tasks
        task_a = Task(func=sync_add, args=(1, 1))
        task_b = Task(func=sync_add, args=(2, 2))
        await omniq.task_queue.enqueue(task_a)
        await omniq.task_queue.enqueue(task_b)

        # Enqueue a task that depends on them
        task_c = Task(func=sync_add, args=(3, 3), dependencies=[task_a.id, task_b.id])
        await omniq.task_queue.enqueue(task_c)

        # Verify task_c is in a 'waiting' state
        stored_task_c = await omniq.task_queue.get_task(task_c.id)
        assert stored_task_c is not None
        assert stored_task_c.status == "waiting"
        assert stored_task_c.dependencies_left == 2

        # Dequeue should only return A and B, not C
        dequeued_a = await omniq.task_queue.dequeue(queues=["default"])
        dequeued_b = await omniq.task_queue.dequeue(queues=["default"])
        assert {dequeued_a.id, dequeued_b.id} == {task_a.id, task_b.id}
        assert await omniq.task_queue.dequeue(queues=["default"], timeout=0) is None

        # Acknowledge task A
        await omniq.task_queue.ack(dequeued_a)

        # Task C should still be waiting
        stored_task_c = await omniq.task_queue.get_task(task_c.id)
        assert stored_task_c.dependencies_left == 1
        assert stored_task_c.status == "waiting"
        assert await omniq.task_queue.dequeue(queues=["default"], timeout=0) is None

        # Acknowledge task B
        await omniq.task_queue.ack(dequeued_b)

        # Now task C should be 'pending' and ready for dequeue
        stored_task_c = await omniq.task_queue.get_task(task_c.id)
        assert stored_task_c.dependencies_left == 0
        assert stored_task_c.status == "pending"

        dequeued_c = await omniq.task_queue.dequeue(queues=["default"])
        assert dequeued_c is not None
        assert dequeued_c.id == task_c.id