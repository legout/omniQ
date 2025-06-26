import asyncio
import time
from unittest.mock import ANY, MagicMock

import pytest

from omniq.serialization import default_serializer
from omniq.workers import AsyncWorker
from tests.helpers import (
    StatefulFailer,
    async_add,
    async_sleep,
    sync_add,
    sync_fail,
)

# --- Fixtures ---


@pytest.fixture
def async_worker(omniq_instance):
    """Provides a default AsyncWorker instance."""
    worker = AsyncWorker(omniq_instance, concurrency=2, queues=["default"])
    return worker


# --- Tests ---


@pytest.mark.asyncio
async def test_async_worker_processes_sync_task(omniq_instance, async_worker):
    """Verify that a sync task is correctly executed and the result is stored."""
    task_id = await omniq_instance.enqueue(sync_add, 1, 2)

    # Run the worker for a short period to process the task
    run_task = asyncio.create_task(async_worker.run())
    await asyncio.sleep(0.1)
    await async_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == 3
    assert result.worker_id == async_worker.worker_id


@pytest.mark.asyncio
async def test_async_worker_processes_async_task(omniq_instance, async_worker):
    """Verify that an async task is correctly executed."""
    task_id = await omniq_instance.enqueue(async_add, 5, 5)

    run_task = asyncio.create_task(async_worker.run())
    await asyncio.sleep(0.1)
    await async_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == 10


@pytest.mark.asyncio
async def test_async_worker_retries_task_on_failure(omniq_instance, async_worker):
    """Verify a task is retried on failure and can succeed on a subsequent attempt."""
    failer = StatefulFailer()
    # dill will serialize the instance and its state
    task_id = await omniq_instance.enqueue(failer.fail_once)

    run_task = asyncio.create_task(async_worker.run())
    await asyncio.sleep(0.2)  # Allow for failure and retry
    await async_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == "Success on attempt 2"


@pytest.mark.asyncio
async def test_async_worker_exceeds_max_retries(omniq_instance, async_worker):
    """Verify a task that repeatedly fails is eventually nacked without requeue."""
    # Spy on the nack method to verify its arguments
    omniq_instance.task_queue.nack = MagicMock(wraps=omniq_instance.task_queue.nack)

    task_id = await omniq_instance.enqueue(sync_fail)

    # Intercept the dequeued task to set its max_retries for a predictable test
    original_dequeue = omniq_instance.task_queue.dequeue

    async def mocked_dequeue(*args, **kwargs):
        task = await original_dequeue(*args, **kwargs)
        if task:
            task.max_retries = 1  # Allow one retry
        return task

    omniq_instance.task_queue.dequeue = mocked_dequeue

    run_task = asyncio.create_task(async_worker.run())
    await asyncio.sleep(0.2)  # Allow time for two failures (initial + 1 retry)
    await async_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "FAILURE"

    # Check that nack was called correctly
    assert omniq_instance.task_queue.nack.call_count == 2
    # First call is to requeue for the retry
    omniq_instance.task_queue.nack.assert_any_call(ANY, requeue=True)
    # Second call is after the retry fails, moving to DLQ (or equivalent)
    omniq_instance.task_queue.nack.assert_any_call(ANY, requeue=False)


@pytest.mark.asyncio
async def test_async_worker_concurrency(omniq_instance, async_worker):
    """Verify that tasks are run concurrently."""
    sleep_duration = 0.2
    num_tasks = 2  # Should match worker concurrency for this test

    for _ in range(num_tasks):
        await omniq_instance.enqueue(async_sleep, sleep_duration)

    start_time = time.monotonic()

    run_task = asyncio.create_task(async_worker.run())
    # Wait long enough for tasks to be processed, but not serially
    await asyncio.sleep(sleep_duration + 0.1)
    await async_worker.shutdown()
    await run_task

    end_time = time.monotonic()

    # With concurrency=2, two 0.2s tasks should take ~0.2s, not 0.4s.
    # We add a buffer for overhead.
    assert (end_time - start_time) < (sleep_duration * num_tasks)
    assert (end_time - start_time) > sleep_duration


@pytest.mark.asyncio
async def test_async_worker_graceful_shutdown(omniq_instance):
    """Verify that shutdown re-queues an in-flight task."""
    worker = AsyncWorker(omniq_instance, concurrency=1)

    task_id = await omniq_instance.enqueue(async_sleep, 5)  # Long-running task

    run_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)  # Give it time to pick up the task

    # Now, shut it down while the task is "running"
    await worker.shutdown()
    await run_task

    # The task should not have completed, so no result should exist
    result = await omniq_instance.get_result(task_id)
    assert result is None

    # The task should have been nacked and re-queued
    requeued_task = await omniq_instance.task_queue.dequeue(["default"])
    assert requeued_task is not None
    assert requeued_task.id == task_id