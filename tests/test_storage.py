"""Tests for FileStorage implementation."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from omniq.models import Task, TaskResult, TaskStatus, Schedule
from omniq.storage.base import TaskError
from omniq.storage.file import FileStorage


class MockSerializer:
    """Mock serializer for testing."""

    def __init__(self):
        self.tasks = {}
        self.results = {}

    async def encode_task(self, task: Task) -> bytes:
        self.tasks[task.id] = task
        import json

        # Serialize task to JSON-compatible format
        task_data = {
            "id": task.id,
            "func_path": task.func_path,
            "args": task.args,
            "kwargs": task.kwargs,
            "schedule": {
                "eta": task.schedule.eta.isoformat(),
                "interval": task.schedule.interval,
                "max_retries": task.schedule.max_retries,
                "timeout": task.schedule.timeout,
            },
            "status": task.status.value,
            "attempt": task.attempt,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "metadata": task.metadata,
        }
        return json.dumps(task_data).encode()

    async def decode_task(self, data: bytes) -> Task:
        import json
        from datetime import datetime

        task_data = json.loads(data.decode())

        # Reconstruct Schedule
        schedule = Schedule(
            eta=datetime.fromisoformat(task_data["schedule"]["eta"]).replace(
                tzinfo=timezone.utc
            ),
            interval=task_data["schedule"]["interval"],
            max_retries=task_data["schedule"]["max_retries"],
            timeout=task_data["schedule"]["timeout"],
        )

        # Reconstruct Task
        return Task(
            id=task_data["id"],
            func_path=task_data["func_path"],
            args=task_data["args"],
            kwargs=task_data["kwargs"],
            schedule=schedule,
            status=TaskStatus(task_data["status"]),
            attempt=task_data["attempt"],
            created_at=datetime.fromisoformat(task_data["created_at"]).replace(
                tzinfo=timezone.utc
            ),
            updated_at=datetime.fromisoformat(task_data["updated_at"]).replace(
                tzinfo=timezone.utc
            ),
            metadata=task_data["metadata"],
        )

    async def encode_result(self, result: TaskResult) -> bytes:
        self.results[result.task_id] = result
        import json

        # Serialize result to JSON-compatible format
        result_data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "result": result.result,
            "error": str(result.error) if result.error else None,
            "attempt": result.attempt,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat()
            if result.completed_at
            else None,
        }
        return json.dumps(result_data).encode()

    async def decode_result(self, data: bytes) -> TaskResult:
        import json
        from datetime import datetime

        result_data = json.loads(data.decode())

        return TaskResult(
            task_id=result_data["task_id"],
            status=TaskStatus(result_data["status"]),
            result=result_data["result"],
            error=Exception(result_data["error"]) if result_data["error"] else None,
            attempt=result_data["attempt"],
            started_at=datetime.fromisoformat(result_data["started_at"]).replace(
                tzinfo=timezone.utc
            )
            if result_data["started_at"]
            else None,
            completed_at=datetime.fromisoformat(result_data["completed_at"]).replace(
                tzinfo=timezone.utc
            )
            if result_data["completed_at"]
            else None,
        )


@pytest.fixture
async def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
async def mock_serializer():
    """Create a mock serializer."""
    return MockSerializer()


@pytest.fixture
async def file_storage(temp_dir, mock_serializer):
    """Create a FileStorage instance for testing."""
    storage = FileStorage(temp_dir, mock_serializer)
    yield storage
    await storage.close()


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_basic(file_storage, mock_serializer):
    """Test basic enqueue and dequeue operations."""
    # Create a task
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))

    # Enqueue the task
    task_id = await file_storage.enqueue(task)
    assert task_id == task.id

    # Dequeue the task
    dequeued_task = await file_storage.dequeue(datetime.now(timezone.utc))
    assert dequeued_task is not None
    assert dequeued_task.id == task.id
    assert dequeued_task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_enqueue_multiple_and_fifo_ordering(file_storage):
    """Test that tasks are dequeued in FIFO order."""
    now = datetime.now(timezone.utc)

    # Create multiple tasks with same ETA
    tasks = []
    for i in range(3):
        task = Task.create(func=lambda x=i: x, eta=now)
        tasks.append(task)
        await file_storage.enqueue(task)

    # Dequeue all tasks
    dequeued_tasks = []
    for _ in range(3):
        task = await file_storage.dequeue(now)
        if task:
            dequeued_tasks.append(task)

    # Should get all tasks back
    assert len(dequeued_tasks) == 3

    # Verify FIFO ordering by task ID (created in order)
    dequeued_ids = [t.id for t in dequeued_tasks]
    original_ids = [t.id for t in tasks]
    assert dequeued_ids == original_ids


@pytest.mark.asyncio
async def test_dequeue_scheduling_by_eta(file_storage):
    """Test that only due tasks are dequeued."""
    now = datetime.now(timezone.utc)
    past = now.replace(second=now.second - 10)
    future = now.replace(second=now.second + 10)

    # Create tasks with different ETAs
    past_task = Task.create(func=lambda: "past", eta=past)
    future_task = Task.create(func=lambda: "future", eta=future)

    await file_storage.enqueue(past_task)
    await file_storage.enqueue(future_task)

    # Should only get the past task
    dequeued = await file_storage.dequeue(now)
    assert dequeued is not None
    assert dequeued.id == past_task.id

    # Future task should not be available yet
    dequeued = await file_storage.dequeue(now)
    assert dequeued is None


@pytest.mark.asyncio
async def test_mark_running_is_noop(file_storage):
    """Test that mark_running is a no-op for FileStorage."""
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # mark_running should not raise any errors
    await file_storage.mark_running(task.id)


@pytest.mark.asyncio
async def test_mark_done_creates_result_file(file_storage):
    """Test that mark_done creates a result file."""
    task = Task.create(func=lambda: "result", eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # Simulate running the task
    await file_storage.dequeue(datetime.now(timezone.utc))

    # Mark as done
    result = TaskResult.success(task.id, "test_result")
    await file_storage.mark_done(task.id, result)

    # Verify result file exists
    result_file = file_storage.results_dir / f"{task.id}.result"
    assert result_file.exists()

    # Verify we can retrieve the result
    retrieved = await file_storage.get_result(task.id)
    assert retrieved is not None
    assert retrieved.task_id == task.id


@pytest.mark.asyncio
async def test_mark_failed_final(file_storage):
    """Test marking task as failed (final)."""
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # Simulate running and failing
    await file_storage.dequeue(datetime.now(timezone.utc))

    error = TaskError(ValueError("Test error"))
    await file_storage.mark_failed(task.id, error, will_retry=False)

    # Verify result file exists
    result = await file_storage.get_result(task.id)
    assert result is not None
    assert result.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_mark_failed_with_retry(file_storage):
    """Test marking task as failed with retry intent."""
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # Simulate running and failing with retry
    await file_storage.dequeue(datetime.now(timezone.utc))

    error = TaskError(ValueError("Test error"))
    await file_storage.mark_failed(task.id, error, will_retry=True)

    # Verify retrying result
    result = await file_storage.get_result(task.id)
    assert result is not None
    assert result.status == TaskStatus.RETRYING


@pytest.mark.asyncio
async def test_get_result_nonexistent(file_storage):
    """Test getting result for non-existent task."""
    result = await file_storage.get_result("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_purge_results(file_storage):
    """Test purging old results."""
    import time
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=1)
    new_time = now + timedelta(days=1)

    # Create some fake result files
    old_result = TaskResult.success("old_task", "old")
    new_result = TaskResult.success("new_task", "new")

    # Manually create result files with different timestamps
    old_file = file_storage.results_dir / "old_task.result"
    new_file = file_storage.results_dir / "new_task.result"

    old_file.touch()
    new_file.touch()

    # Set different modification times
    import os

    os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
    os.utime(new_file, (new_time.timestamp(), new_time.timestamp()))

    # Purge old results
    purged = await file_storage.purge_results(now)
    assert purged >= 1

    # Old file should be gone
    assert not old_file.exists()
    # New file should remain
    assert new_file.exists()


@pytest.mark.asyncio
async def test_reschedule_task(file_storage):
    """Test rescheduling a task."""
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # Simulate taking the task
    await file_storage.dequeue(datetime.now(timezone.utc))

    # Reschedule for future
    from datetime import timedelta

    new_eta = datetime.now(timezone.utc) + timedelta(seconds=60)
    await file_storage.reschedule(task.id, new_eta)

    # Should be able to dequeue again (task is back in queue)
    dequeued = await file_storage.dequeue(new_eta)
    assert dequeued is not None
    assert dequeued.id == task.id


@pytest.mark.asyncio
async def test_atomic_rename_concurrent_dequeue(file_storage):
    """Test that concurrent dequeues don't claim the same task twice."""
    task = Task.create(func=lambda: None, eta=datetime.now(timezone.utc))
    await file_storage.enqueue(task)

    # Simulate multiple concurrent dequeues
    async def dequeue_task():
        return await file_storage.dequeue(datetime.now(timezone.utc))

    # Run multiple dequeues concurrently
    results = await asyncio.gather(*[dequeue_task() for _ in range(3)])

    # Only one should get the task, others should get None
    claimed_tasks = [r for r in results if r is not None]
    assert len(claimed_tasks) == 1
    assert claimed_tasks[0].id == task.id
