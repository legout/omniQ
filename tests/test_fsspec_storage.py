import asyncio
import os
import shutil

import pytest

from omniq import OmniQ
from omniq.models import Task, TaskResult
from omniq.serialization import default_serializer


@pytest.fixture
def temp_dir():
    """Create and clean up a temporary directory for testing."""
    path = "test_fsspec_storage"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    yield path
    shutil.rmtree(path)


@pytest.fixture
def fsspec_omniq(temp_dir):
    """Provides an OmniQ instance with fsspec storage (local file system)."""
    return OmniQ(
        task_queue_url=f"file://{temp_dir}/tasks",
        result_storage_url=f"file://{temp_dir}/results",
    )


@pytest.mark.asyncio
async def test_fsspec_task_queue_enqueue_dequeue(fsspec_omniq, temp_dir):
    """Test enqueueing and dequeuing a task from the FsspecTaskQueue."""
    task = Task(func=lambda x: x * 2, args=(5,), kwargs={}, queue="test_queue")
    task_id = await fsspec_omniq.task_queue.enqueue(task)

    # Check if the file was created
    task_file_path = os.path.join(temp_dir, "tasks", "test_queue", task_id)
    assert os.path.exists(task_file_path)

    # Dequeue the task
    dequeued_task = await fsspec_omniq.task_queue.dequeue(["test_queue"])
    assert dequeued_task is not None
    assert dequeued_task.id == task.id
    assert dequeued_task.func == task.func
    assert dequeued_task.args == task.args
    assert dequeued_task.kwargs == task.kwargs

    # Verify that the task file has moved to processing
    processing_path = f"{task_file_path}.processing"
    assert os.path.exists(processing_path)
    assert not os.path.exists(task_file_path)

    # Acknowledge the task
    await fsspec_omniq.task_queue.ack(dequeued_task)
    assert not os.path.exists(processing_path)


@pytest.mark.asyncio
async def test_fsspec_task_queue_nack_requeue(fsspec_omniq, temp_dir):
    """Test negatively acknowledging a task and requeuing it."""
    task = Task(func=lambda x: x * 2, args=(5,), kwargs={}, queue="test_queue")
    await fsspec_omniq.task_queue.enqueue(task)

    dequeued_task = await fsspec_omniq.task_queue.dequeue(["test_queue"])
    assert dequeued_task is not None

    # Nack and requeue the task
    await fsspec_omniq.task_queue.nack(dequeued_task, requeue=True)

    # Verify the processing file is back in the queue
    task_file_path = os.path.join(temp_dir, "tasks", "test_queue", dequeued_task.id)
    processing_path = f"{task_file_path}.processing"
    assert not os.path.exists(processing_path)
    assert os.path.exists(task_file_path)

    # Dequeue again to confirm it was requeued
    requeued_task = await fsspec_omniq.task_queue.dequeue(["test_queue"])
    assert requeued_task is not None
    assert requeued_task.id == task.id

    await fsspec_omniq.task_queue.ack(requeued_task)


@pytest.mark.asyncio
async def test_fsspec_result_storage_store_get_delete(fsspec_omniq):
    """Test storing, retrieving, and deleting a task result."""
    result = TaskResult(
        task_id="test_task_123",
        status="SUCCESS",
        result=default_serializer.serialize("task completed successfully"),
        started_at=1678886400.0,
        completed_at=1678886410.0,
        worker_id="test_worker",
    )

    # Store the result
    await fsspec_omniq.result_storage.store(result)

    # Retrieve the result
    retrieved_result = await fsspec_omniq.result_storage.get("test_task_123")
    assert retrieved_result is not None
    assert retrieved_result.task_id == result.task_id
    assert retrieved_result.status == result.status
    assert (
        default_serializer.deserialize(retrieved_result.result)
        == "task completed successfully"
    )
    assert retrieved_result.worker_id == result.worker_id

    # Delete the result
    await fsspec_omniq.result_storage.delete("test_task_123")
    deleted_result = await fsspec_omniq.result_storage.get("test_task_123")
    assert deleted_result is None