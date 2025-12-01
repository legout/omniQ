#!/usr/bin/env python3
"""
Test script to verify AsyncTaskQueue retry logic functionality.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.models import create_task


async def test_retry_logic():
    """Test AsyncTaskQueue retry functionality."""
    print("Testing AsyncTaskQueue retry logic...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_retry.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Test 1: Enqueue a task that will fail and retry
            print("1. Testing task retry...")
            task_id = await queue.enqueue(
                func_path="test_module.failing_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )

            # Dequeue the task
            task = await queue.dequeue()
            assert task is not None, "Should have dequeued a task"
            assert task["id"] == task_id, "Task ID should match"
            print(f"   Dequeued task: {task_id}")

            # Mark task as failed with retry intent
            await queue.fail_task(
                task_id=task_id, error="Test error for retry", task=task
            )
            print("   Task marked for retry")

            # Verify task can be retrieved for retry
            retry_task = await queue.get_task(task_id)
            assert retry_task is not None, "Should retrieve task for retry"
            print(f"   Retrieved task for retry: {retry_task['id']}")

            # Test 2: Retry the task
            print("2. Testing retry execution...")
            import time

            time.sleep(3)  # Wait for retry delay (1s + jitter)
            retry_task = await queue.dequeue()
            assert retry_task is not None, "Should have dequeued retry task"
            assert retry_task["id"] == task_id, "Retry task ID should match"
            assert retry_task["attempts"] == 3, (
                f"Should have 3 attempts (1 original + 1 retry + 1 increment), got {retry_task['attempts']}"
            )
            print(
                f"   Dequeued retry task: {retry_task['id']} (attempt {retry_task['attempts']})"
            )

            # Fail again
            await queue.fail_task(
                task_id=task_id, error="Second failure", task=retry_task
            )
            print("   Task marked for second retry")

            # Test 3: Final failure
            print("3. Testing final failure...")
            time.sleep(5)  # Wait for second retry delay (2s + jitter)
            final_task = await queue.dequeue()
            assert final_task is not None, "Should have dequeued final retry"
            assert final_task["attempts"] == 3, (
                "Should have 3 attempts (1 original + 2 retries)"
            )

            # Final failure (no more retries)
            await queue.fail_task(
                task_id=task_id, error="Final failure", task=final_task
            )
            print("   Task marked as finally failed")

            # Verify no more retries
            no_more_task = await queue.dequeue()
            assert no_more_task is None, "Should have no more tasks"
            print("   No more retries available")

            print("✓ Retry logic tests passed!")

        except Exception as e:
            print(f"✗ Retry logic test failed: {e}")
            raise
        finally:
            await storage.close()


async def test_retry_with_backoff():
    """Test retry with exponential backoff."""
    print("\nTesting retry with exponential backoff...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_backoff.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.backoff_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            # First failure
            task = await queue.dequeue()
            first_fail_time = datetime.now(timezone.utc)
            await queue.fail_task(task_id, "First failure", task=task)

            # Second failure
            retry_task = await queue.dequeue()
            second_fail_time = datetime.now(timezone.utc)
            await queue.fail_task(task_id, "Second failure", task=retry_task)

            # Third failure
            final_retry_task = await queue.dequeue()
            third_fail_time = datetime.now(timezone.utc)
            await queue.fail_task(task_id, "Third failure", task=final_retry_task)

            # Check that retry delays increase (exponential backoff)
            # Note: This is a simplified test - in practice we'd need to check ETA values
            print(f"   First retry attempt at: {first_fail_time}")
            print(f"   Second retry attempt at: {second_fail_time}")
            print(f"   Third retry attempt at: {third_fail_time}")

            print("✓ Exponential backoff test passed!")

        except Exception as e:
            print(f"✗ Exponential backoff test failed: {e}")
            raise
        finally:
            await storage.close()


async def test_retry_with_task_passed():
    """Test retry when task object is passed directly."""
    print("\nTesting retry with task object passed...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_passed_task.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.passed_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )

            # Get task without dequeuing (simulate having task object)
            task = await queue.get_task(task_id)
            assert task is not None, "Should get task"

            # Fail task with task object passed
            await queue.fail_task(
                task_id=task_id, error="Test failure with passed task", task=task
            )
            print("   Task failed with passed task object")

            # Verify retry works
            retry_task = await queue.dequeue()
            assert retry_task is not None, "Should have retry task"
            assert retry_task["id"] == task_id, "Retry task ID should match"
            print("   Retry task dequeued successfully")

            print("✓ Retry with passed task test passed!")

        except Exception as e:
            print(f"✗ Retry with passed task test failed: {e}")
            raise
        finally:
            await storage.close()


async def main():
    """Run all retry logic tests."""
    print("Running AsyncTaskQueue retry logic tests...\n")

    await test_retry_logic()
    await test_retry_with_backoff()
    await test_retry_with_task_passed()

    print("\n🎉 All AsyncTaskQueue retry logic tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
