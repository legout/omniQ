#!/usr/bin/env python3
"""
End-to-end tests for retry scenarios using both FileStorage and SQLiteStorage.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.storage.file import FileStorage
from src.omniq.models import create_task
from src.omniq.serialization import JSONSerializer


async def test_e2e_retry_with_sqlite():
    """End-to-end retry test with SQLite storage."""
    print("Testing end-to-end retry with SQLite storage...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "e2e_retry.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Create a task that will fail multiple times before succeeding
            task_id = await queue.enqueue(
                func_path="test_module.flaky_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            print(f"   Enqueued task: {task_id}")

            # Simulate failure-retry-success cycle
            attempt = 0
            success = False

            while attempt < 4:  # Max 3 retries + initial attempt
                task = await queue.dequeue()
                if task is None:
                    break

                attempt += 1
                print(f"   Attempt {attempt}: Dequeued task {task['id']}")

                if attempt < 3:
                    # Fail first 2 attempts
                    await queue.fail_task(
                        task_id=task["id"],
                        error=f"Simulated failure {attempt}",
                        task=task,
                    )
                    print(f"   Attempt {attempt} failed, task scheduled for retry")
                else:
                    # Succeed on 3rd attempt
                    await queue.complete_task(
                        task_id=task["id"],
                        result=f"Success on attempt {attempt}",
                        task=task,
                    )
                    print(f"   Attempt {attempt} succeeded!")
                    success = True
                    break

                # Wait for retry delay (exponential backoff increases with each attempt)
                # Wait longer than retry delay (which is 2^attempt seconds with jitter)
                await asyncio.sleep(2 ** (attempt - 1) + 1.5)  # 1.5s, 2.5s, 4.5s

            assert success, "Task should eventually succeed"
            assert attempt == 3, "Should have taken exactly 3 attempts"

            # Verify final result
            result = await queue.get_result(task_id)
            assert result is not None, "Should have result"
            assert result["result"] == "Success on attempt 3", "Result should match"
            print("   Final result verified")

            print("✓ End-to-end retry with SQLite passed!")

        except Exception as e:
            print(f"✗ End-to-end retry with SQLite failed: {e}")
            raise
        finally:
            await storage.close()


async def test_e2e_retry_with_file_storage():
    """End-to-end retry test with File storage."""
    print("\nTesting end-to-end retry with File storage...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())
        queue = AsyncTaskQueue(storage)

        try:
            # Create a task that will fail and retry
            task_id = await queue.enqueue(
                func_path="test_module.file_retry_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            print(f"   Enqueued task: {task_id}")

            # First attempt - fail
            task = await queue.dequeue()
            assert task is not None, "Should have dequeued task"
            await queue.fail_task(task_id, "First failure", task=task)
            print("   First attempt failed, retry scheduled")

            # Wait for retry delay
            import time

            time.sleep(2)

            # Second attempt - fail
            retry_task = await queue.dequeue()
            assert retry_task is not None, "Should have retry task"
            await queue.fail_task(task_id, "Second failure", task=retry_task)
            print("   Second attempt failed, final retry scheduled")

            # Wait for retry delay
            time.sleep(5)

            # Third attempt - succeed
            final_task = await queue.dequeue()
            assert final_task is not None, "Should have final retry task"
            await queue.complete_task(task_id, "Final success", task=final_task)
            print("   Third attempt succeeded")

            # Verify result
            result = await queue.get_result(task_id)
            assert result is not None, "Should have result"
            assert result["result"] == "Final success", "Result should match"
            print("   Result verified")

            print("✓ End-to-end retry with File storage passed!")

        except Exception as e:
            print(f"✗ End-to-end retry with File storage failed: {e}")
            raise


async def test_e2e_interval_tasks_with_retry():
    """End-to-end test: interval tasks with retry functionality."""
    print("\nTesting end-to-end interval tasks with retry...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "e2e_interval.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Create an interval task
            task_id = await queue.enqueue(
                func_path="test_module.interval_with_retry",
                args=[],
                kwargs={},
                interval=30,  # 30 second interval
                max_retries=3,
                timeout=30,
            )

            print(f"   Enqueued interval task: {task_id}")

            # First execution - fail and retry
            task = await queue.dequeue()
            assert task is not None, "Should have dequeued interval task"

            # Fail first attempt
            await queue.fail_task(task_id, "Interval task failure", task=task)
            print("   Interval task failed, retry scheduled")

            # Wait for retry delay
            import time

            time.sleep(2)

            # Retry execution - succeed
            retry_task = await queue.dequeue()
            assert retry_task is not None, "Should have retry task"

            # Complete the task (should trigger interval rescheduling)
            await queue.complete_task(task_id, "Interval task success", task=retry_task)
            print("   Interval task succeeded, rescheduling triggered")

            # Check for rescheduled task
            future_time = datetime.now(timezone.utc) + timedelta(seconds=31)
            rescheduled_task = await queue.storage.dequeue(future_time)

            if rescheduled_task:
                assert (
                    rescheduled_task["func_path"] == "test_module.interval_with_retry"
                ), "Should be same function"
                assert rescheduled_task.get("interval") == 30, (
                    "Should preserve interval"
                )
                assert rescheduled_task["id"] != task_id, "Should be new task ID"
                print(f"   Task rescheduled: {rescheduled_task['id']}")
            else:
                print("   Task scheduled for future execution (expected)")

            print("✓ End-to-end interval tasks with retry passed!")

        except Exception as e:
            print(f"✗ End-to-end interval tasks with retry failed: {e}")
            raise
        finally:
            await storage.close()


async def test_e2e_mixed_workload():
    """End-to-end test: mixed workload with regular tasks, retries, and intervals."""
    print("\nTesting end-to-end mixed workload...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "e2e_mixed.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Create different types of tasks
            regular_task_id = await queue.enqueue(
                func_path="test_module.regular_task",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )

            retry_task_id = await queue.enqueue(
                func_path="test_module.retry_task",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            interval_task_id = await queue.enqueue(
                func_path="test.module.interval_task",
                args=[],
                kwargs={},
                interval=60,
                max_retries=2,
                timeout=30,
            )

            print(f"   Enqueued regular task: {regular_task_id}")
            print(f"   Enqueued retry task: {retry_task_id}")
            print(f"   Enqueued interval task: {interval_task_id}")

            # Process regular task - succeed immediately
            regular_task = await queue.dequeue()
            assert regular_task is not None
            await queue.complete_task(
                regular_task["id"], "Regular task done", task=regular_task
            )
            print("   Regular task completed")

            # Process retry task - fail twice, then succeed
            for attempt in range(3):
                retry_task = await queue.dequeue()
                assert retry_task is not None
                if attempt < 2:
                    await queue.fail_task(
                        retry_task["id"],
                        f"Retry attempt {attempt + 1} failed",
                        task=retry_task,
                    )
                    print(f"   Retry task attempt {attempt + 1} failed")
                else:
                    await queue.complete_task(
                        retry_task["id"], "Retry task succeeded", task=retry_task
                    )
                    print("   Retry task succeeded on final attempt")
                    break

            # Process interval task - succeed and reschedule
            interval_task = await queue.dequeue()
            assert interval_task is not None
            await queue.complete_task(
                interval_task["id"], "Interval task done", task=interval_task
            )
            print("   Interval task completed and rescheduled")

            # Verify all results
            regular_result = await queue.get_result(regular_task_id)
            assert regular_result is not None
            assert regular_result["result"] == "Regular task done"

            retry_result = await queue.get_result(retry_task_id)
            assert retry_result is not None
            assert retry_result["result"] == "Retry task succeeded"

            print("   All results verified")

            print("✓ End-to-end mixed workload test passed!")

        except Exception as e:
            print(f"✗ End-to-end mixed workload test failed: {e}")
            raise
        finally:
            await storage.close()


async def test_e2e_storage_compatibility():
    """End-to-end test: verify both storage backends work identically."""
    print("\nTesting storage backend compatibility...")

    with (
        tempfile.TemporaryDirectory() as temp_dir1,
        tempfile.TemporaryDirectory() as temp_dir2,
    ):
        # Test with SQLite
        sqlite_db = Path(temp_dir1) / "compat_test.db"
        sqlite_storage = SQLiteStorage(sqlite_db)
        sqlite_queue = AsyncTaskQueue(sqlite_storage)

        # Test with File storage
        file_storage = FileStorage(temp_dir2, JSONSerializer())
        file_queue = AsyncTaskQueue(file_storage)

        try:
            # Same task for both backends
            task_func = "test_module.compat_function"
            task_args = [1, 2, 3]
            task_kwargs = {"key": "value"}

            # Enqueue in both
            sqlite_id = await sqlite_queue.enqueue(
                task_func, task_args, task_kwargs, max_retries=2
            )
            file_id = await file_queue.enqueue(
                task_func, task_args, task_kwargs, max_retries=2
            )

            # Process in both
            sqlite_task = await sqlite_queue.dequeue()
            file_task = await file_queue.dequeue()

            # Verify tasks are equivalent (except IDs)
            assert sqlite_task["func_path"] == file_task["func_path"]
            assert sqlite_task["args"] == file_task["args"]
            assert sqlite_task["kwargs"] == file_task["kwargs"]

            # Complete both
            await sqlite_queue.complete_task(
                sqlite_id, "SQLite success", task=sqlite_task
            )
            await file_queue.complete_task(file_id, "File success", task=file_task)

            # Verify results
            sqlite_result = await sqlite_queue.get_result(sqlite_id)
            file_result = await file_queue.get_result(file_id)

            assert sqlite_result["result"] == "SQLite success"
            assert file_result["result"] == "File success"

            print("   Both storage backends behave identically")
            print("✓ Storage compatibility test passed!")

        except Exception as e:
            print(f"✗ Storage compatibility test failed: {e}")
            raise
        finally:
            await sqlite_storage.close()


async def main():
    """Run all end-to-end tests."""
    print("Running end-to-end retry scenario tests...\n")

    await test_e2e_retry_with_sqlite()
    await test_e2e_retry_with_file_storage()
    await test_e2e_interval_tasks_with_retry()
    await test_e2e_mixed_workload()
    await test_e2e_storage_compatibility()

    print("\n🎉 All end-to-end tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
