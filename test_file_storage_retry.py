#!/usr/bin/env python3
"""
Test script to verify FileStorage retry functionality with the fixed state machine.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from src.omniq.storage.file import FileStorage
from src.omniq.models import TaskStatus, create_task
from src.omniq.serialization import JSONSerializer


async def test_file_storage_retry_flow():
    """Test FileStorage retry flow for retryable failures."""
    print("Testing FileStorage retry flow...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Create a task with retries
            task = create_task(
                func_path="test_module.retry_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            task_id = await storage.enqueue(task)
            print(f"   Enqueued task: {task_id}")

            # Test 1: Dequeue task (should mark as RUNNING)
            now = datetime.now(timezone.utc)
            dequeued_task = await storage.dequeue(now)
            assert dequeued_task is not None, "Should have dequeued a task"
            assert dequeued_task["id"] == task_id, "Task ID should match"
            assert dequeued_task["status"] == TaskStatus.RUNNING, (
                "Task should be RUNNING"
            )
            assert dequeued_task["attempts"] == 1, "Should have 1 attempt"
            print(f"   Dequeued task: {task_id} (attempt {dequeued_task['attempts']})")

            # Test 2: Mark task as failed with retry intent
            await storage.mark_failed(task_id, "First failure", will_retry=True)
            print("   Task marked for retry")

            # Test 3: Verify task is in FAILED state after failure
            failed_task = await storage.get_task(task_id)
            assert failed_task is not None, "Should retrieve failed task"
            assert failed_task["status"] == TaskStatus.FAILED, (
                "Task should be FAILED after failure"
            )
            assert failed_task["attempts"] == 1, "Attempts should still be 1"
            print(f"   Task in FAILED state after failure: {failed_task['id']}")

            # Test 4: Reschedule task for retry (transitions to PENDING)
            retry_eta = datetime.now(timezone.utc) + timedelta(seconds=1)
            await storage.reschedule(task_id, retry_eta)

            # Verify task is now PENDING for retry
            retry_task = await storage.get_task(task_id)
            assert retry_task is not None, "Should retrieve task for retry"
            assert retry_task["status"] == TaskStatus.PENDING, (
                "Task should be PENDING after reschedule"
            )
            assert retry_task["attempts"] == 1, "Attempts should still be 1"
            print(f"   Task rescheduled and in PENDING state: {retry_task['id']}")

            # Test 5: Dequeue task for retry (use time after eta)
            dequeue_time = retry_eta + timedelta(seconds=1)
            print(f"   Attempting to dequeue at time: {dequeue_time}")
            print(f"   Retry eta was: {retry_eta}")
            retry_task = await storage.dequeue(dequeue_time)
            if retry_task is None:
                # Debug: check what files exist
                task_files = list(Path(temp_dir).glob("queue/*"))
                print(f"   Available files: {[f.name for f in task_files]}")
                # Check task status directly
                current_task = await storage.get_task(task_id)
                if current_task:
                    task_eta = current_task["schedule"].get("eta")
                    print(f"   Current task status: {current_task['status']}")
                    print(f"   Task eta: {task_eta}")
                    print(f"   Task eta type: {type(task_eta)}")
                    print(f"   Dequeue time type: {type(dequeue_time)}")
                    print(
                        f"   eta <= now: {task_eta <= dequeue_time if task_eta else 'No eta'}"
                    )
            assert retry_task is not None, "Should have dequeued retry task"
            assert retry_task["id"] == task_id, "Retry task ID should match"
            assert retry_task["status"] == TaskStatus.RUNNING, "Task should be RUNNING"
            assert retry_task["attempts"] == 2, "Should have 2 attempts"
            print(
                f"   Dequeued retry task: {task_id} (attempt {retry_task['attempts']})"
            )

            # Test 6: Second failure with retry
            await storage.mark_failed(task_id, "Second failure", will_retry=True)
            print("   Task marked for second retry")

            # Test 7: Reschedule for second retry
            retry_eta2 = datetime.now(timezone.utc) + timedelta(seconds=1)
            await storage.reschedule(task_id, retry_eta2)

            # Test 8: Dequeue for second retry
            dequeue_time2 = retry_eta2 + timedelta(seconds=1)
            final_retry_task = await storage.dequeue(dequeue_time2)
            assert final_retry_task is not None, "Should have dequeued final retry"
            assert final_retry_task["attempts"] == 3, "Should have 3 attempts"
            print(
                f"   Dequeued final retry: {task_id} (attempt {final_retry_task['attempts']})"
            )

            print("✓ FileStorage retry flow test passed!")

        except Exception as e:
            print(f"✗ FileStorage retry flow test failed: {e}")
            raise


async def test_file_storage_final_failure():
    """Test FileStorage final failure when retries are exhausted."""
    print("\nTesting FileStorage final failure...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Create a task with 1 retry
            task = create_task(
                func_path="test_module.final_failure_function",
                args=[],
                kwargs={},
                max_retries=1,
                timeout=30,
            )
            task_id = await storage.enqueue(task)

            # First attempt
            now = datetime.now(timezone.utc)
            dequeued_task = await storage.dequeue(now)
            assert dequeued_task["attempts"] == 1, "First attempt should be 1"

            # First failure (will retry)
            await storage.mark_failed(task_id, "First failure", will_retry=True)
            await storage.reschedule(task_id, datetime.now(timezone.utc))

            # Second attempt (retry)
            retry_task = await storage.dequeue(datetime.now(timezone.utc))
            assert retry_task["attempts"] == 2, "Retry attempt should be 2"

            # Final failure (no more retries)
            await storage.mark_failed(task_id, "Final failure", will_retry=False)
            print("   Task marked as finally failed")

            # Verify task is in FAILED state
            failed_task = await storage.get_task(task_id)
            assert failed_task is not None, "Should retrieve failed task"
            print(f"   Task status after final failure: {failed_task['status']}")
            assert failed_task["status"] == TaskStatus.FAILED, "Task should be FAILED"
            assert failed_task["attempts"] == 2, "Should have 2 attempts total"
            print(f"   Task in FAILED state: {task_id}")

            # Verify no more tasks can be dequeued
            no_more_task = await storage.dequeue(datetime.now(timezone.utc))
            assert no_more_task is None, "Should have no more tasks"
            print("   No more tasks available for dequeue")

            print("✓ FileStorage final failure test passed!")

        except Exception as e:
            print(f"✗ FileStorage final failure test failed: {e}")
            raise


async def test_file_storage_retry_state_consistency():
    """Test that FileStorage retry maintains state consistency."""
    print("\nTesting FileStorage retry state consistency...")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(temp_dir, JSONSerializer())

        try:
            # Create task
            task = create_task(
                func_path="test_module.state_consistency_function",
                args=[],
                kwargs={},
                max_retries=2,
                timeout=30,
            )
            task_id = await storage.enqueue(task)

            # Test state transitions through retry cycle
            # 1. Initial state: PENDING
            pending_task = await storage.get_task(task_id)
            assert pending_task["status"] == TaskStatus.PENDING, (
                "Should start as PENDING"
            )

            # 2. After dequeue: RUNNING
            now = datetime.now(timezone.utc)
            running_task = await storage.dequeue(now)
            assert running_task["status"] == TaskStatus.RUNNING, (
                "Should be RUNNING after dequeue"
            )

            # 3. After failure with retry: FAILED (until rescheduled)
            await storage.mark_failed(task_id, "Test failure", will_retry=True)
            failed_task = await storage.get_task(task_id)
            assert failed_task["status"] == TaskStatus.FAILED, (
                "Should be FAILED after failure with retry"
            )
            print("   ✓ After failure with retry: FAILED")

            # 4. After reschedule: PENDING
            await storage.reschedule(task_id, datetime.now(timezone.utc))
            retry_pending_task = await storage.get_task(task_id)
            assert retry_pending_task["status"] == TaskStatus.PENDING, (
                "Should be PENDING after reschedule"
            )
            print("   ✓ After reschedule: PENDING")

            # 5. After retry dequeue: RUNNING
            retry_running_task = await storage.dequeue(datetime.now(timezone.utc))
            assert retry_running_task["status"] == TaskStatus.RUNNING, (
                "Should be RUNNING on retry"
            )
            print("   ✓ After retry dequeue: RUNNING")

            # 6. After final failure: FAILED
            await storage.mark_failed(task_id, "Final failure", will_retry=False)
            final_failed_task = await storage.get_task(task_id)
            assert final_failed_task["status"] == TaskStatus.FAILED, (
                "Should be FAILED after final failure"
            )
            print("   ✓ After final failure: FAILED")

            print("   All state transitions are consistent")
            print("✓ FileStorage retry state consistency test passed!")

        except Exception as e:
            print(f"✗ FileStorage retry state consistency test failed: {e}")
            raise


async def main():
    """Run all FileStorage retry tests."""
    print("Running FileStorage retry tests...\n")

    await test_file_storage_retry_flow()
    await test_file_storage_final_failure()
    await test_file_storage_retry_state_consistency()

    print("\n🎉 All FileStorage retry tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
