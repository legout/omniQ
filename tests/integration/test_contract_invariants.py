"""
Contract tests for core OmniQ invariants.
These tests verify critical behaviors that must not regress.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta

from omniq.models import create_task, transition_status, TaskStatus
from omniq.storage.sqlite import SQLiteStorage
from omniq.storage.file import FileStorage
from omniq.queue import AsyncTaskQueue
from omniq.serialization import JSONSerializer


class TestAtomicClaim:
    """Test that dequeue provides atomic, single-transaction claims."""

    @pytest.mark.asyncio
    async def test_sqlite_atomic_claim(self, temp_dir):
        """SQLite must claim task in single atomic transaction."""
        from pathlib import Path

        db_path = Path(temp_dir) / "atomic_claim.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        task_id = await queue.enqueue(
            func_path="test_func",
            args=[],
            kwargs={},
        )

        # Dequeue once
        task1 = await queue.dequeue()
        assert task1 is not None
        assert task1["status"] == TaskStatus.RUNNING
        assert task1["attempts"] == 1

        # Verify only one UPDATE happened by checking persisted state
        # Get task again to verify database state
        task_check = await storage.get_task(task_id)
        assert task_check["status"] == TaskStatus.RUNNING
        assert task_check["attempts"] == 1

        # If duplicate UPDATE statements were run, attempts might be 2+
        # Single-transaction should keep it at 1
        assert task_check["attempts"] == 1, "Attempts should increment exactly once"

        await storage.close()


class TestAttemptCounting:
    """Test that attempts increment exactly once per claim."""

    @pytest.mark.asyncio
    async def test_attempts_increment_on_each_dequeue(self, temp_dir):
        """Attempts must increment on each PENDING→RUNNING transition."""
        from pathlib import Path

        storage = SQLiteStorage(Path(temp_dir) / "attempts.db")
        queue = AsyncTaskQueue(storage)

        task_id = await queue.enqueue(
            func_path="test_func",
            args=[],
            kwargs={},
            max_retries=3,
        )

        # First dequeue
        task1 = await queue.dequeue()
        assert task1["attempts"] == 1

        # Simulate failure and reschedule
        await queue.fail_task(task_id, "Test failure", task=task1)

        # Wait for retry delay
        await asyncio.sleep(1.5)

        # Second dequeue
        task2 = await queue.dequeue()
        assert task2["attempts"] == 2

        await storage.close()


class TestRetryBudgetEnforcement:
    """Test that retry budget is enforced correctly with '<' operator."""

    @pytest.mark.asyncio
    async def test_retry_budget_with_less_than(self, temp_dir):
        """Retry predicate must use '<' not '<='."""
        from pathlib import Path

        storage = SQLiteStorage(Path(temp_dir) / "budget.db")
        queue = AsyncTaskQueue(storage)

        # max_retries=3 means max 3 executions (attempts 0, 1, 2)
        # Task should NOT retry on attempt 3 because 3 < 3 is False
        task_id = await queue.enqueue(
            func_path="test_func",
            args=[],
            kwargs={},
            max_retries=3,
        )

        # First dequeue (attempts=0 → 1)
        task1 = await queue.dequeue()
        assert task1["attempts"] == 1

        # Fail and retry
        await queue.fail_task(task_id, "Failure 1", task=task1)
        await asyncio.sleep(1.5)

        # Second dequeue (attempts=1 → 2)
        task2 = await queue.dequeue()
        assert task2["attempts"] == 2

        # Fail and retry
        await queue.fail_task(task_id, "Failure 2", task=task2)
        await asyncio.sleep(2.5)

        # Third dequeue (attempts=2 → 3)
        task3 = await queue.dequeue()
        assert task3["attempts"] == 3

        # Fail - should NOT retry because 3 < 3 is False
        await queue.fail_task(task_id, "Final failure", task=task3)

        # No more tasks available
        task4 = await queue.dequeue()
        assert task4 is None, "Should not retry when attempts >= max_retries"

        await storage.close()


class TestNoDoubleReschedule:
    """Test that retry scheduling happens exactly once."""

    @pytest.mark.asyncio
    async def test_fail_task_creates_single_retry(self, temp_dir):
        """fail_task() must schedule exactly one retry, not multiple."""
        from pathlib import Path

        storage = SQLiteStorage(Path(temp_dir) / "single_retry.db")
        queue = AsyncTaskQueue(storage)

        task_id = await queue.enqueue(
            func_path="test_func",
            args=[],
            kwargs={},
            max_retries=2,
        )

        # First attempt
        task1 = await queue.dequeue()
        await queue.fail_task(task_id, "Failure", task=task1)

        # Check task result (should show failed state)
        # Note: Task itself will be PENDING (ready for retry) after reschedule
        # This is expected behavior in simplified state machine
        result = await storage.get_result(task_id)
        assert result is not None
        assert result["status"] == TaskStatus.FAILED
        assert result["attempts"] == 1

        # Wait for eta
        await asyncio.sleep(1.5)

        # Second attempt (should succeed)
        task2 = await queue.dequeue()
        assert task2["attempts"] == 2
        assert task2["id"] == task_id

        # Complete task
        await queue.complete_task(task_id, "Success", task=task2)

        # Verify no additional rescheduling happened
        task_final = await storage.get_task(task_id)
        assert task_final["status"] == TaskStatus.SUCCESS

        await storage.close()
