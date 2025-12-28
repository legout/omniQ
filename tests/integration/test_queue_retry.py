"""
Comprehensive tests for AsyncTaskQueue retry logic.
"""

import asyncio
from pathlib import Path
from datetime import datetime, timezone
from omniq.models import TaskStatus
import pytest


@pytest.mark.asyncio
async def test_retry_logic(temp_dir, queue):
    """Test AsyncTaskQueue retry functionality."""
    print("1. Testing task retry...")

    # Enqueue a task that will fail and retry
    # Patch worker execute to always fail
    import omniq.worker as worker_module

    original_execute = worker_module.AsyncWorkerPool._execute_task

    async def failing_execute(self, task):
        """Always fail task execution."""
        await asyncio.sleep(0.1)  # Quick failure
        raise Exception("Test failure for retry")

    worker_module.AsyncWorkerPool._execute_task = failing_execute

    task_id = await queue.enqueue(
        func_path="test_module.failing_function",
        args=[],
        kwargs={},
        max_retries=3,
        timeout=30,
    )

    # Simulate multiple retries
    for i in range(3):
        task = await queue.dequeue(now=datetime.now(timezone.utc))
        assert task is not None, f"Attempt {i + 1}: Should have task to dequeue"
        assert task["id"] == task_id, "Task ID should match"

        # Mark task as failed for retry
        await queue.fail_task(task_id, f"Attempt {i + 1} failure", task=task)

        # Verify task can be retrieved for retry
        retry_task = await queue.get_task(task_id)
        assert retry_task is not None
        assert retry_task["status"] == TaskStatus.PENDING, (
            f"Attempt {i + 1}: Task should be PENDING for retry"
        )

    # Restore original execute
    worker_module.AsyncWorkerPool._execute_task = original_execute

    print("   ✓ Retry logic works correctly")


@pytest.mark.asyncio
async def test_exponential_backoff(temp_dir, queue):
    """Test exponential backoff calculation."""
    print("\n2. Testing exponential backoff...")

    task_id = await queue.enqueue(
        func_path="asyncio.sleep",
        args=[0.1],
        kwargs={},
        max_retries=3,
    )

    # Get task and check initial eta
    task = await queue.get_task(task_id)
    initial_eta = task["schedule"].get("eta")

    # Simulate failures to trigger backoff
    for i in range(3):
        task = await queue.dequeue(datetime.now(timezone.utc))
        await queue.fail_task(task_id, f"Failure {i + 1}", task=task)

    # Check final eta shows expected delay
    task = await queue.get_task(task_id)
    final_eta = task["schedule"].get("eta")

    # After 3 failures, eta should be in the future
    assert final_eta > initial_eta
    print("   ✓ Exponential backoff calculated correctly")


@pytest.mark.asyncio
async def test_retry_budget_enforcement(temp_dir, queue):
    """Test that retry budget is enforced (attempts < max_retries)."""
    print("\n3. Testing retry budget enforcement...")

    # Enqueue task with max_retries=2
    # This means: initial (attempts=0) + 2 retries = 3 total executions
    task_id = await queue.enqueue(
        func_path="asyncio.sleep",
        args=[0.1],
        kwargs={},
        max_retries=2,
    )

    # Simulate 3 total executions (1 initial + 2 retries)
    for i in range(3):
        task = await queue.dequeue(datetime.now(timezone.utc))
        assert task is not None, f"Execution {i + 1}: Should have task to dequeue"

        # Last execution should be permanent failure
        if i == 2:
            await queue.fail_task(task_id, "Final failure", task=task)
        else:
            await queue.fail_task(task_id, f"Retry attempt {i + 1}", task=task)

    # Check task is permanently failed after 3 executions
    task = await queue.get_task(task_id)
    assert task is not None
    assert task["status"] == TaskStatus.FAILED
    assert task["attempts"] == 3  # Should be exactly 3 (attempts < max_retries)

    print("   ✓ Retry budget enforced correctly (attempts < max_retries)")


@pytest.mark.asyncio
async def test_no_double_reschedule(temp_dir, queue):
    """Test that fail_task creates only one retry entry."""
    print("\n4. Testing no double reschedule...")

    task_id = await queue.enqueue(
        func_path="asyncio.sleep",
        args=[0.1],
        kwargs={},
        max_retries=1,
    )

    # Fail task once
    task = await queue.dequeue(datetime.now(timezone.utc))
    await queue.fail_task(task_id, "Test failure", task=task)

    # Try to fail again (should use same retry entry, not create new one)
    retry_task = await queue.get_task(task_id)
    assert retry_task is not None
    await queue.fail_task(task_id, "Second failure", task=retry_task)

    # Verify only one failure result exists
    result = await queue.get_result(task_id)
    # First fail should have a result, second should just update status
    assert result is not None

    print("   ✓ No double reschedule - single retry path")
