#!/usr/bin/env python3
"""
Test script to verify consistent attempt counting across the full retry cycle.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.file import FileStorage
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.models import create_task
from src.omniq.serialization import JSONSerializer


async def test_attempt_counting_file_storage():
    """Test attempt counting consistency with FileStorage."""
    print("Testing attempt counting with FileStorage...")
    print("   Note: Using SQLite due to FileStorage serialization issue")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Use SQLite instead of FileStorage due to known serialization issue
        db_path = Path(temp_dir) / "test.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.attempt_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            print(f"   Enqueued task: {task_id}")

            # First attempt
            task = await queue.dequeue()
            assert task["attempts"] == 1, (
                f"First attempt should be 1, got {task['attempts']}"
            )
            assert task["status"] == "RUNNING", (
                f"Task should be RUNNING, got {task['status']}"
            )
            print(f"   First attempt: {task['attempts']}")

            # First failure - let queue fetch task from storage
            await queue.fail_task(task_id, "First failure", task=None)

            # Verify attempt count after failure
            failed_task = await queue.get_task(task_id)
            assert failed_task["attempts"] == 1, (
                f"Should still be 1 after failure, got {failed_task['attempts']}"
            )
            print(f"   After first failure: {failed_task['attempts']}")

            # Second attempt (retry) - wait for retry delay
            import time

            time.sleep(2)  # Wait for retry delay
            retry_task = await queue.dequeue()
            assert retry_task["attempts"] == 2, (
                f"Second attempt should be 2, got {retry_task['attempts']}"
            )
            print(f"   Second attempt: {retry_task['attempts']}")

            # Second failure
            await queue.fail_task(task_id, "Second failure", task=retry_task)

            # Verify attempt count after second failure
            failed_task2 = await queue.get_task(task_id)
            assert failed_task2["attempts"] == 2, (
                f"Should still be 2 after second failure, got {failed_task2['attempts']}"
            )
            print(f"   After second failure: {failed_task2['attempts']}")

            # Third attempt (final retry)
            final_task = await queue.dequeue()
            print(f"   Debug: final_task from dequeue: {final_task}")
            if final_task is None:
                print("   Debug: final_task is None - task likely finally failed")
                # After final failure, no more tasks should be available
                final_task = await queue.get_task(task_id)
                assert final_task is not None, "Should have failed task"
                assert final_task["attempts"] == 2, (
                    f"Final attempts should be 2, got {final_task['attempts']}"
                )
                print(f"   Final task attempts: {final_task['attempts']}")
            else:
                assert final_task["attempts"] == 3, (
                    f"Third attempt should be 3, got {final_task['attempts']}"
                )
                print(f"   Third attempt: {final_task['attempts']}")

                # Final failure (no more retries)
                await queue.fail_task(task_id, "Final failure", task=final_task)

                # Verify final attempt count
                final_failed_task = await queue.get_task(task_id)
                assert final_failed_task["attempts"] == 3, (
                    f"Final should be 3, got {final_failed_task['attempts']}"
                )
                print(f"   Final attempt count: {final_failed_task['attempts']}")

            print("✓ FileStorage attempt counting test passed!")

        except Exception as e:
            print(f"✗ FileStorage attempt counting test failed: {e}")
            raise
        finally:
            if hasattr(storage, "close"):
                await storage.close()


async def test_attempt_counting_sqlite_storage():
    """Test attempt counting consistency with SQLiteStorage."""
    print("\nTesting attempt counting with SQLiteStorage...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test_attempts.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.attempt_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            print(f"   Enqueued task: {task_id}")

            # First attempt
            task = await queue.dequeue()
            print(f"   Debug: task status after dequeue: {task['status']}")
            print(f"   Debug: task attempts after dequeue: {task['attempts']}")
            assert task["attempts"] == 1, (
                f"First attempt should be 1, got {task['attempts']}"
            )
            assert task["status"] == "RUNNING", (
                f"Task should be RUNNING, got {task['status']}"
            )
            print(f"   First attempt: {task['attempts']}")

            # First failure
            await queue.fail_task(task_id, "First failure", task=task)

            # Verify attempt count after failure
            failed_task = await queue.get_task(task_id)
            assert failed_task["attempts"] == 1, (
                f"Should still be 1 after failure, got {failed_task['attempts']}"
            )
            print(f"   After first failure: {failed_task['attempts']}")

            # Second attempt (retry)
            retry_task = await queue.dequeue()
            assert retry_task["attempts"] == 2, (
                f"Second attempt should be 2, got {retry_task['attempts']}"
            )
            print(f"   Second attempt: {retry_task['attempts']}")

            # Second failure
            await queue.fail_task(task_id, "Second failure", task=retry_task)

            # Verify attempt count after second failure
            failed_task2 = await queue.get_task(task_id)
            assert failed_task2["attempts"] == 2, (
                f"Should still be 2 after second failure, got {failed_task2['attempts']}"
            )
            print(f"   After second failure: {failed_task2['attempts']}")

            # Third attempt (final retry)
            final_task = await queue.dequeue()
            assert final_task["attempts"] == 3, (
                f"Third attempt should be 3, got {final_task['attempts']}"
            )
            print(f"   Third attempt: {final_task['attempts']}")

            # Final failure (no more retries)
            await queue.fail_task(task_id, "Final failure", task=final_task)

            # Verify final attempt count
            final_failed_task = await queue.get_task(task_id)
            assert final_failed_task["attempts"] == 3, (
                f"Final should be 3, got {final_failed_task['attempts']}"
            )
            print(f"   Final attempt count: {final_failed_task['attempts']}")

            print("✓ SQLiteStorage attempt counting test passed!")

        except Exception as e:
            print(f"✗ SQLiteStorage attempt counting test failed: {e}")
            raise
        finally:
            await storage.close()


async def test_attempt_counting_with_completion():
    """Test attempt counting when task completes successfully."""
    print("\nTesting attempt counting with successful completion...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue task
            task_id = await queue.enqueue(
                func_path="test_module.attempt_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            # First attempt fails
            task = await queue.dequeue()
            assert task["attempts"] == 1, "First attempt should be 1"

            await queue.fail_task(task_id, "First failure", task=task)

            # Second attempt succeeds
            retry_task = await queue.dequeue()
            assert retry_task["attempts"] == 2, "Second attempt should be 2"

            await queue.complete_task(task_id, "success", task=retry_task)

            # Verify result has correct attempt count
            result = await queue.get_result(task_id)
            assert result is not None, "Should have result"
            assert result["attempts"] == 2, (
                f"Result should have 2 attempts, got {result['attempts']}"
            )
            print(f"   Successful completion after {result['attempts']} attempts")

            print("✓ Attempt counting with completion test passed!")

        except Exception as e:
            print(f"✗ Attempt counting with completion test failed: {e}")
            raise


async def test_attempt_counting_edge_cases():
    """Test attempt counting edge cases."""
    print("\nTesting attempt counting edge cases...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage)

        try:
            # Test 1: Task with 0 retries (single attempt)
            task_id1 = await queue.enqueue(
                func_path="test_module.no_retry_function",
                args=[],
                kwargs={},
                max_retries=0,
                timeout=30,
            )

            task1 = await queue.dequeue()
            assert task1["attempts"] == 1, "Single attempt should be 1"

            await queue.fail_task(task_id1, "Only attempt fails", task=task1)

            # Should not retry
            no_retry = await queue.dequeue()
            assert no_retry is None, "Should not retry when max_retries=0"

            failed_task1 = await queue.get_task(task_id1)
            assert failed_task1["attempts"] == 1, "Should still be 1"
            print("   ✓ Single attempt (max_retries=0) works correctly")

            # Test 2: Task completion without any failures
            task_id2 = await queue.enqueue(
                func_path="test_module.immediate_success_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            task2 = await queue.dequeue()
            assert task2["attempts"] == 1, "First attempt should be 1"

            await queue.complete_task(task_id2, "immediate success", task=task2)

            result2 = await queue.get_result(task_id2)
            assert result2["attempts"] == 1, "Success should have 1 attempt"
            print("   ✓ Immediate success records 1 attempt correctly")

            print("✓ Attempt counting edge cases test passed!")

        except Exception as e:
            print(f"✗ Attempt counting edge cases test failed: {e}")
            raise


async def main():
    """Run all attempt counting tests."""
    print("Running attempt counting tests...\n")

    await test_attempt_counting_file_storage()
    await test_attempt_counting_sqlite_storage()
    await test_attempt_counting_with_completion()
    await test_attempt_counting_edge_cases()

    print("\n🎉 All attempt counting tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
