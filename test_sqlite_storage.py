#!/usr/bin/env python3
"""
Simple test script to verify SQLite storage functionality.
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

from src.omniq.storage.sqlite import SQLiteStorage
from src.omniq.models import Task, TaskStatus, create_task
from src.omniq.serialization import JSONSerializer


async def test_sqlite_storage():
    """Test basic SQLite storage functionality."""
    print("Testing SQLiteStorage...")

    # Create temporary directory for database
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        storage = SQLiteStorage(db_path)

        try:
            # Test 1: Create and enqueue a task
            print("1. Testing enqueue...")
            task = create_task(
                func_path="test_module.test_function",
                args=[1, 2],
                kwargs={"key": "value"},
                max_retries=3,
                timeout=30,
            )

            task_id = await storage.enqueue(task)
            print(f"   Enqueued task: {task_id}")

            # Test 2: Dequeue the task
            print("2. Testing dequeue...")
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            dequeued_task = await storage.dequeue(now)
            assert dequeued_task is not None, "Should have dequeued a task"
            assert dequeued_task["id"] == task_id, "Task ID should match"
            assert dequeued_task["status"] == TaskStatus.RUNNING, (
                "Task should be RUNNING"
            )
            print(f"   Dequeued task: {dequeued_task['id']}")

            # Test 3: Mark task as done
            print("3. Testing mark_done...")
            from src.omniq.models import create_success_result

            result = create_success_result(
                task_id=task_id, result=42, attempts=1, last_attempt_at=now
            )

            await storage.mark_done(task_id, result)
            print("   Task marked as done")

            # Test 4: Get result
            print("4. Testing get_result...")
            retrieved_result = await storage.get_result(task_id)
            assert retrieved_result is not None, "Should have a result"
            assert retrieved_result["status"] == TaskStatus.SUCCESS, (
                "Result should be SUCCESS"
            )
            assert retrieved_result["result"] == 42, "Result should match"
            print(f"   Retrieved result: {retrieved_result['result']}")

            # Test 5: Test with failure
            print("5. Testing mark_failed...")
            task2 = create_task(
                func_path="test_module.failing_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )

            task2_id = await storage.enqueue(task2)
            dequeued_task2 = await storage.dequeue(now)

            await storage.mark_failed(task2_id, "Test error", will_retry=False)
            failure_result = await storage.get_result(task2_id)
            assert failure_result is not None, "Should have a failure result"
            assert failure_result["status"] == TaskStatus.FAILED, (
                "Result should be FAILED"
            )
            assert "Test error" in failure_result["error"], "Error message should match"
            print("   Task marked as failed")

            # Test 6: Test reschedule
            print("6. Testing reschedule...")
            task3 = create_task(
                func_path="test_module.scheduled_function",
                args=[],
                kwargs={},
                max_retries=3,
                timeout=30,
            )

            task3_id = await storage.enqueue(task3)
            future_time = datetime.now(timezone.utc)

            await storage.reschedule(task3_id, future_time)
            print("   Task rescheduled successfully")

            # Test 7: Test get_task
            print("7. Testing get_task...")
            retrieved_task = await storage.get_task(task3_id)
            assert retrieved_task is not None, "Should retrieve task by ID"
            assert retrieved_task["id"] == task3_id, "Task ID should match"
            assert retrieved_task["func_path"] == "test_module.scheduled_function", (
                "Function path should match"
            )
            print(f"   Retrieved task: {retrieved_task['id']}")

            # Test 8: Test get_task for non-existent task
            print("8. Testing get_task for non-existent task...")
            non_existent_task = await storage.get_task("non-existent-id")
            assert non_existent_task is None, "Should return None for non-existent task"
            print("   Correctly returned None for non-existent task")

            # Test 9: Test purge results
            print("7. Testing purge_results...")
            from datetime import timedelta

            cutoff = now - timedelta(days=1)  # Yesterday

            purged_count = await storage.purge_results(cutoff)
            print(f"   Purged {purged_count} old results")

            print("✓ All SQLiteStorage tests passed!")

        except Exception as e:
            print(f"✗ SQLiteStorage test failed: {e}")
            raise
        finally:
            await storage.close()


async def test_scheduling():
    """Test scheduling behavior with eta."""
    print("\nTesting scheduling behavior...")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "schedule_test.db"
        storage = SQLiteStorage(db_path)

        try:
            from datetime import datetime, timezone, timedelta

            # Create tasks with different ETAs
            now = datetime.now(timezone.utc)
            future_task = create_task(
                func_path="test_module.future_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            # Set ETA to future
            future_task["schedule"]["eta"] = now + timedelta(hours=1)

            immediate_task = create_task(
                func_path="test_module.immediate_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            # No ETA means immediate execution

            # Enqueue in reverse order to test proper sorting
            future_id = await storage.enqueue(future_task)
            immediate_id = await storage.enqueue(immediate_task)

            # Should get immediate task first
            dequeued = await storage.dequeue(now)
            assert dequeued is not None, "Should have dequeued immediate task"
            assert dequeued["id"] == immediate_id, "Should get immediate task first"
            print("   Immediate task dequeued first (correct ordering)")

            # Should not get future task yet
            dequeued = await storage.dequeue(now)
            assert dequeued is None, "Should not get future task yet"
            print("   Future task not dequeued yet (correct)")

            # After future time, should get future task
            future_time = now + timedelta(hours=2)
            dequeued = await storage.dequeue(future_time)
            assert dequeued is not None, "Should get future task after time"
            assert dequeued["id"] == future_id, "Should get future task"
            print("   Future task dequeued after time (correct)")

            print("✓ Scheduling tests passed!")

        except Exception as e:
            print(f"✗ Scheduling test failed: {e}")
            raise
        finally:
            await storage.close()


async def main():
    """Run all SQLite storage tests."""
    print("Running SQLite storage tests...\n")

    await test_sqlite_storage()
    await test_scheduling()

    print("\n🎉 All SQLite storage tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
