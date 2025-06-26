import asyncio
import time
from unittest.mock import ANY, MagicMock

import pytest

from omniq.serialization import default_serializer
from omniq.workers import ThreadPoolWorker
from tests.helpers import (
    StatefulFailer,
    async_add,
    sync_add,
    sync_fail,
    sync_sleep,
)

# --- Fixtures ---


@pytest.fixture
def thread_worker(omniq_instance):
    """Provides a default ThreadPoolWorker instance."""
    worker = ThreadPoolWorker(omniq_instance, concurrency=2, queues=["default"])
    return worker


# --- Tests ---


@pytest.mark.asyncio
async def test_thread_worker_processes_sync_task(omniq_instance, thread_worker):
    """Verify that a sync task is correctly executed and the result is stored."""
    task_id = await omniq_instance.enqueue(sync_add, 1, 2)

    run_task = asyncio.create_task(thread_worker.run())
    await asyncio.sleep(0.1)
    await thread_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == 3
    assert result.worker_id == thread_worker.worker_id


@pytest.mark.asyncio
async def test_thread_worker_processes_async_task(omniq_instance, thread_worker):
    """Verify that an async task is correctly executed by the thread worker."""
    task_id = await omniq_instance.enqueue(async_add, 5, 5)

    run_task = asyncio.create_task(thread_worker.run())
    await asyncio.sleep(0.1)
    await thread_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == 10


@pytest.mark.asyncio
async def test_thread_worker_retries_task_on_failure(omniq_instance, thread_worker):
    """Verify a task is retried on failure and can succeed on a subsequent attempt."""
    failer = StatefulFailer()
    task_id = await omniq_instance.enqueue(failer.fail_once)

    run_task = asyncio.create_task(thread_worker.run())
    await asyncio.sleep(0.2)  # Allow for failure and retry
    await thread_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == "Success on attempt 2"


@pytest.mark.asyncio
async def test_thread_worker_exceeds_max_retries(omniq_instance, thread_worker):
    """Verify a task that repeatedly fails is eventually nacked without requeue."""
    omniq_instance.task_queue.nack = MagicMock(wraps=omniq_instance.task_queue.nack)
    task_id = await omniq_instance.enqueue(sync_fail)

    original_dequeue = omniq_instance.task_queue.dequeue
    async def mocked_dequeue(*args, **kwargs):
        task = await original_dequeue(*args, **kwargs)
        if task:
            task.max_retries = 1
        return task
    omniq_instance.task_queue.dequeue = mocked_dequeue

    run_task = asyncio.create_task(thread_worker.run())
    await asyncio.sleep(0.2)
    await thread_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "FAILURE"
    assert omniq_instance.task_queue.nack.call_count == 2
    omniq_instance.task_queue.nack.assert_any_call(ANY, requeue=True)
    omniq_instance.task_queue.nack.assert_any_call(ANY, requeue=False)


@pytest.mark.asyncio
async def test_thread_worker_concurrency(omniq_instance, thread_worker):
    """Verify that tasks are run concurrently in threads."""
    sleep_duration = 0.2
    num_tasks = 2  # Should match worker concurrency

    for _ in range(num_tasks):
        await omniq_instance.enqueue(sync_sleep, sleep_duration)

    start_time = time.monotonic()

    run_task = asyncio.create_task(thread_worker.run())
    await asyncio.sleep(sleep_duration + 0.1)
    await thread_worker.shutdown()
    await run_task

    end_time = time.monotonic()

    # With concurrency=2, two blocking 0.2s tasks should take ~0.2s, not 0.4s.
    assert (end_time - start_time) < (sleep_duration * num_tasks)
    assert (end_time - start_time) > sleep_duration


@pytest.mark.asyncio
async def test_thread_worker_graceful_shutdown(omniq_instance):
    """
    Verify that shutdown waits for an in-flight task to complete.
    This is different from AsyncWorker, which would cancel and requeue.
    """
    worker = ThreadPoolWorker(omniq_instance, concurrency=1)
    task_id = await omniq_instance.enqueue(sync_sleep, 0.2)

    run_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)  # Give it time to pick up the task

    shutdown_start_time = time.monotonic()
    await worker.shutdown()
    await run_task
    shutdown_duration = time.monotonic() - shutdown_start_time

    # The shutdown should have been blocked by the running task.
    # It should take at least the remaining task time to complete.
    assert shutdown_duration > 0.1

    # The task should have completed and its result stored.
    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"

    # The queue should now be empty.
    requeued_task = await omniq_instance.task_queue.dequeue(["default"])
    assert requeued_task is None