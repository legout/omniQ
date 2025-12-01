#!/usr/bin/env python3
"""
Basic OmniQ usage example with retry functionality.
"""

import asyncio
import tempfile
from pathlib import Path

from src.omniq.queue import AsyncTaskQueue
from src.omniq.storage.sqlite import SQLiteStorage


async def flaky_function(task_id: str):
    """A function that fails a few times before succeeding."""
    # Simulate failure by checking attempt count
    # In real usage, you'd track this differently
    import random

    if random.random() < 0.7:  # 70% chance of failure
        raise Exception(f"Random failure in task {task_id}")
    return f"Success for task {task_id}"


async def basic_retry_example():
    """Example of basic retry functionality."""
    print("=== Basic Retry Example ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "basic_retry.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue a task with retry configuration
            task_id = await queue.enqueue(
                func_path="examples.basic.flaky_function",
                args=["task-123"],
                kwargs={},
                max_retries=3,  # Retry up to 3 times
                timeout=30,
            )
            print(f"Enqueued task: {task_id}")

            # Simulate worker processing
            for attempt in range(4):  # Max 3 retries + initial
                task = await queue.dequeue()
                if task is None:
                    break

                print(f"Attempt {attempt + 1}: Processing task {task['id']}")

                try:
                    # Simulate task execution
                    result = await flaky_function(task["id"])
                    await queue.complete_task(task["id"], result, task=task)
                    print(f"✓ Task completed: {result}")
                    break
                except Exception as e:
                    print(f"✗ Task failed: {e}")
                    await queue.fail_task(task["id"], str(e), task=task)

            # Check final result
            result = await queue.get_result(task_id)
            if result:
                print(f"Final result: {result['result']}")
            else:
                print("Task failed permanently")

        finally:
            await storage.close()


async def interval_task_with_retry_example():
    """Example of interval task with retry support."""
    print("\n=== Interval Task with Retry Example ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "interval_retry.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue an interval task with retry
            task_id = await queue.enqueue(
                func_path="examples.basic.monitor_function",
                args=["system-health"],
                kwargs={"threshold": 0.8},
                interval=60,  # Every 60 seconds
                max_retries=2,  # Retry failed checks
                timeout=30,
            )
            print(f"Enqueued interval task: {task_id}")

            # Simulate a few executions
            for i in range(3):
                task = await queue.dequeue()
                if task is None:
                    break

                print(f"Execution {i + 1}: Processing interval task {task['id']}")

                try:
                    # Simulate monitoring check
                    result = f"Monitor check {i + 1} completed"
                    await queue.complete_task(task["id"], result, task=task)
                    print(f"✓ {result}")

                    # Note: In real usage, the next execution would be scheduled
                    # automatically after the interval passes

                except Exception as e:
                    print(f"✗ Monitor check failed: {e}")
                    await queue.fail_task(task["id"], str(e), task=task)

        finally:
            await storage.close()


async def custom_retry_behavior_example():
    """Example of custom retry behavior."""
    print("\n=== Custom Retry Behavior Example ===")

    class CustomQueue(AsyncTaskQueue):
        """Custom queue with modified retry behavior."""

        def _should_retry(self, task, attempts):
            """Don't retry certain error types."""
            error = task.get("last_error", "").lower()
            if "authentication" in error or "permission" in error:
                return False  # Don't retry auth/permission errors
            return super()._should_retry(task, attempts)

        def _calculate_retry_delay(self, retry_count):
            """Custom delay: shorter for network errors, longer for others."""
            return min(retry_count * 2, 30)  # 2s, 4s, 6s, max 30s

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "custom_retry.db"
        storage = SQLiteStorage(db_path)
        queue = CustomQueue(storage)

        try:
            # Task with authentication error (won't retry)
            auth_task_id = await queue.enqueue(
                func_path="examples.basic.api_call",
                args=["protected-endpoint"],
                kwargs={},
                max_retries=5,  # High limit, but won't retry auth errors
                timeout=30,
            )
            print(f"Enqueued auth task: {auth_task_id}")

            # Simulate auth failure
            auth_task = await queue.dequeue()
            await queue.fail_task(
                auth_task["id"],
                "Authentication failed: Invalid credentials",
                task=auth_task,
            )
            print("Auth task failed (no retries due to auth error)")

            # Task with network error (will retry)
            net_task_id = await queue.enqueue(
                func_path="examples.basic.network_call",
                args=["api-endpoint"],
                kwargs={},
                max_retries=3,
                timeout=30,
            )
            print(f"Enqueued network task: {net_task_id}")

            # Simulate network failure and retry
            for attempt in range(3):
                task = await queue.dequeue()
                if task is None or task["id"] != net_task_id:
                    break

                print(f"Network attempt {attempt + 1}")
                await queue.fail_task(
                    task["id"], f"Network timeout (attempt {attempt + 1})", task=task
                )

        finally:
            await storage.close()


async def monitoring_retries_example():
    """Example of monitoring retry patterns."""
    print("\n=== Monitoring Retries Example ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "monitoring.db"
        storage = SQLiteStorage(db_path)
        queue = AsyncTaskQueue(storage)

        try:
            # Enqueue multiple tasks with different retry characteristics
            tasks = []

            # Network task (more retries)
            net_task = await queue.enqueue(
                func_path="examples.api.fetch_data",
                args=["https://api.example.com/data"],
                kwargs={},
                max_retries=5,
                timeout=30,
            )
            tasks.append(("network", net_task))

            # Database task (fewer retries)
            db_task = await queue.enqueue(
                func_path="examples.db.update_record",
                args=["users", 123, {"status": "active"}],
                kwargs={},
                max_retries=2,
                timeout=10,
            )
            tasks.append(("database", db_task))

            # File task (minimal retries)
            file_task = await queue.enqueue(
                func_path="examples.file.process_upload",
                args=["upload.csv"],
                kwargs={},
                max_retries=1,
                timeout=60,
            )
            tasks.append(("file", file_task))

            print(f"Enqueued {len(tasks)} tasks with different retry limits")

            # Simulate processing and monitor
            retry_stats = {}

            for task_type, task_id in tasks:
                attempts = 0
                success = False

                while attempts < 6:  # Safety limit
                    task = await queue.dequeue()
                    if task is None or task["id"] != task_id:
                        break

                    attempts += 1
                    print(f"{task_type.title()} task attempt {attempts}")

                    # Simulate different failure rates
                    import random

                    if task_type == "network" and random.random() < 0.6:
                        await queue.fail_task(task["id"], "Network timeout", task=task)
                    elif task_type == "database" and random.random() < 0.3:
                        await queue.fail_task(
                            task["id"], "Database constraint", task=task
                        )
                    elif task_type == "file" and random.random() < 0.2:
                        await queue.fail_task(task["id"], "File corrupted", task=task)
                    else:
                        await queue.complete_task(
                            task["id"], f"{task_type} success", task=task
                        )
                        success = True
                        break

                retry_stats[task_type] = {"attempts": attempts, "success": success}
                print(
                    f"{task_type.title()} task: {'✓ Success' if success else '✗ Failed'} after {attempts} attempts"
                )

            # Summary
            print("\nRetry Summary:")
            for task_type, stats in retry_stats.items():
                print(
                    f"  {task_type.title()}: {stats['attempts']} attempts, {'Success' if stats['success'] else 'Failed'}"
                )

        finally:
            await storage.close()


async def main():
    """Run all examples."""
    print("OmniQ Retry Examples\n")

    await basic_retry_example()
    await interval_task_with_retry_example()
    await custom_retry_behavior_example()
    await monitoring_retries_example()

    print("\n🎉 All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
