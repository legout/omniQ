import asyncio
import time

import pytest

from omniq.serialization import default_serializer
from omniq.workers import ProcessPoolWorker
from tests.helpers import StatefulFailer, cpu_intensive_task, sync_add

# --- Fixtures ---


@pytest.fixture
def process_worker(omniq_instance):
    """Provides a default ProcessPoolWorker instance."""
    # Use concurrency=2 for concurrency tests
    worker = ProcessPoolWorker(omniq_instance, concurrency=2, queues=["default"])
    return worker


# --- Tests ---


@pytest.mark.asyncio
async def test_process_worker_processes_sync_task(omniq_instance, process_worker):
    """Verify that a simple sync task is correctly executed in a child process."""
    task_id = await omniq_instance.enqueue(sync_add, 5, 10)

    run_task = asyncio.create_task(process_worker.run())
    await asyncio.sleep(0.2)  # Give time for process startup and execution
    await process_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == 15
    # Worker ID will have the process PID appended
    assert result.worker_id.startswith(process_worker.worker_id)


@pytest.mark.asyncio
async def test_process_worker_retries_task_on_failure(omniq_instance, process_worker):
    """Verify a task is retried on failure across processes."""
    failer = StatefulFailer()
    task_id = await omniq_instance.enqueue(failer.fail_once)

    run_task = asyncio.create_task(process_worker.run())
    await asyncio.sleep(0.3)  # Allow for failure and retry
    await process_worker.shutdown()
    await run_task

    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"
    assert default_serializer.deserialize(result.result) == "Success on attempt 2"


@pytest.mark.asyncio
async def test_process_worker_concurrency(omniq_instance, process_worker):
    """Verify that CPU-bound tasks are run concurrently in separate processes."""
    # A number that takes a fraction of a second to count to
    iterations = 10_000_000
    num_tasks = 2  # Should match worker concurrency

    # To get a baseline, run one task first
    single_task_id = await omniq_instance.enqueue(cpu_intensive_task, iterations)
    single_run_task = asyncio.create_task(process_worker.run())
    await asyncio.sleep(0.1)
    start_single = time.monotonic()
    while not await omniq_instance.get_result(single_task_id):
        await asyncio.sleep(0.05)
    single_duration = time.monotonic() - start_single
    await process_worker.shutdown()
    await single_run_task

    # Now, run two tasks and measure
    task_ids = [
        await omniq_instance.enqueue(cpu_intensive_task, iterations)
        for _ in range(num_tasks)
    ]

    start_time = time.monotonic()
    run_task = asyncio.create_task(process_worker.run())

    # Wait until both results are available
    for tid in task_ids:
        while not await omniq_instance.get_result(tid):
            await asyncio.sleep(0.05)

    end_time = time.monotonic()
    await process_worker.shutdown()
    await run_task

    total_duration = end_time - start_time

    # With true parallelism, the total time should be slightly more than a single
    # task's duration, but significantly less than the sum of both.
    assert total_duration < (single_duration * num_tasks * 0.9)
    assert total_duration > single_duration


@pytest.mark.asyncio
async def test_process_worker_graceful_shutdown(omniq_instance):
    """Verify that shutdown waits for an in-flight CPU-bound task to complete."""
    worker = ProcessPoolWorker(omniq_instance, concurrency=1)
    task_id = await omniq_instance.enqueue(cpu_intensive_task, 10_000_000)

    run_task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)  # Give it time to pick up the task

    shutdown_start_time = time.monotonic()
    await worker.shutdown()
    await run_task
    shutdown_duration = time.monotonic() - shutdown_start_time

    # The shutdown should have been blocked by the running task.
    assert shutdown_duration > 0.1

    # The task should have completed and its result stored.
    result = await omniq_instance.get_result(task_id)
    assert result is not None
    assert result.status == "SUCCESS"