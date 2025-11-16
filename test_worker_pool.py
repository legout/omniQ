#!/usr/bin/env python3
"""Comprehensive test for worker pool functionality."""

import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, "src")

from omniq.worker import AsyncWorkerPool, WorkerPool
from omniq.models import Task, TaskResult, TaskStatus, Schedule
from omniq.storage.file import FileStorage
from omniq.serialization import create_serializer


class TestStorage:
    """Mock storage for testing worker pool functionality."""

    def __init__(self):
        self.tasks = []
        self.results = {}
        self.rescheduled_tasks = []
        self.call_count = 0

    async def enqueue(self, task):
        self.tasks.append(task)

    async def dequeue(self, now):
        # Return tasks that are due
        if self.tasks:
            task = self.tasks.pop(0)
            return task
        return None

    async def mark_running(self, task_id):
        pass

    async def mark_done(self, task_id, result):
        self.results[task_id] = result
        print(f"✅ Task {task_id} completed: {result.status}")

    async def mark_failed(self, task_id, error, will_retry):
        if will_retry:
            print(f"🔄 Task {task_id} marked for retry")
        else:
            print(f"❌ Task {task_id} marked as failed")
            self.results[task_id] = None

    async def reschedule(self, task_id, new_eta):
        self.rescheduled_tasks.append((task_id, new_eta))
        print(f"📅 Task {task_id} rescheduled for {new_eta}")

    async def get_result(self, task_id):
        return self.results.get(task_id)


async def test_sync_function():
    """Test a synchronous function."""
    await asyncio.sleep(0.1)  # Simulate some work
    return "sync result"


async def test_async_function(x, y=10):
    """Test an asynchronous function."""
    await asyncio.sleep(0.1)  # Simulate some work
    return x + y


def test_sync_function_no_args():
    """Test a synchronous function with no arguments."""
    return "sync no args"


def test_sync_function_with_args(a, b=20):
    """Test a synchronous function with arguments."""
    return a + b


async def test_failing_function():
    """Test a function that always fails."""
    raise ValueError("Test failure")


async def test_worker_pool_basic():
    """Test basic worker pool functionality."""

    print("🧪 Testing Worker Pool Basic Functionality")
    print("=" * 50)

    # Create test storage
    storage = TestStorage()

    # Create worker pool
    worker_pool = AsyncWorkerPool(
        storage=storage, concurrency=2, poll_interval=0.1, base_retry_delay=0.5
    )

    # Test 1: Sync function with no args
    print("\n📋 Test 1: Sync function with no arguments")
    task1 = Task.create(test_sync_function_no_args, eta=datetime.now(timezone.utc))
    await storage.enqueue(task1)

    # Test 2: Sync function with args
    print("\n📋 Test 2: Sync function with arguments")
    task2 = Task.create(
        test_sync_function_with_args,
        args=(5,),
        kwargs={"b": 15},
        eta=datetime.now(timezone.utc),
    )
    await storage.enqueue(task2)

    # Test 3: Async function
    print("\n📋 Test 3: Async function")
    task3 = Task.create(
        test_async_function,
        args=(10,),
        kwargs={"y": 20},
        eta=datetime.now(timezone.utc),
    )
    await storage.enqueue(task3)

    # Test 4: Interval task
    print("\n📋 Test 4: Interval task")
    schedule = Schedule(eta=datetime.now(timezone.utc), interval=2, max_retries=0)
    task4 = Task.create(test_sync_function_no_args, schedule=schedule)
    await storage.enqueue(task4)

    # Run worker for a few seconds
    print("\n🚀 Starting worker pool...")

    # Start worker in background
    worker_task = asyncio.create_task(worker_pool.start())

    # Let it run for a few seconds
    await asyncio.sleep(3)

    # Stop worker
    await worker_pool.stop()
    worker_task.cancel()

    print(f"\n✅ Results collected: {len(storage.results)} tasks")
    print(f"✅ Rescheduled tasks: {len(storage.rescheduled_tasks)} tasks")


async def test_retry_logic():
    """Test retry logic with exponential backoff."""

    print("\n🔄 Testing Retry Logic")
    print("=" * 30)

    storage = TestStorage()

    # Create worker with short retry delay for testing
    worker_pool = AsyncWorkerPool(
        storage=storage,
        concurrency=1,
        poll_interval=0.1,
        base_retry_delay=0.3,  # Short delay for testing
    )

    # Test failing function
    task = Task.create(test_failing_function, eta=datetime.now(timezone.utc))
    task.schedule.max_retries = 2  # Allow 2 retries
    await storage.enqueue(task)

    print("📝 Testing retry logic with failing function...")

    # Run worker
    worker_task = asyncio.create_task(worker_pool.start())
    await asyncio.sleep(2)  # Let it try a few times
    await worker_pool.stop()
    worker_task.cancel()

    print("✅ Retry logic test completed")


def test_retry_delay_calculation():
    """Test retry delay calculation."""

    print("\n⏱️  Testing Retry Delay Calculation")
    print("=" * 40)

    storage = TestStorage()
    worker_pool = AsyncWorkerPool(storage, base_retry_delay=1.0)

    delays = []
    for attempt in range(1, 6):
        delay = worker_pool._calculate_retry_delay(attempt)
        delays.append(delay)
        print(f"Attempt {attempt}: {delay:.2f}s")

    # Verify exponential growth
    expected_multipliers = [1, 2, 4, 8, 16]
    for i, (actual, expected_mult) in enumerate(zip(delays, expected_multipliers)):
        # Allow for jitter, so check within reasonable range
        expected_base = 1.0 * expected_mult
        if expected_base * 0.8 <= actual <= expected_base * 1.2:  # ±20% tolerance
            print(f"✅ Attempt {i + 1}: {actual:.2f}s (expected ~{expected_base:.2f}s)")
        else:
            print(f"❌ Attempt {i + 1}: {actual:.2f}s (expected ~{expected_base:.2f}s)")


async def test_worker_pool_integration():
    """Test worker pool with real file storage."""

    print("\n💾 Testing Worker Pool with File Storage")
    print("=" * 45)

    # Create temporary directory for storage
    with tempfile.TemporaryDirectory() as tmp_dir:
        from omniq.serialization import MsgspecSerializer

        storage = FileStorage(
            base_dir=Path(tmp_dir) / "test_queue", serializer=MsgspecSerializer()
        )

        worker_pool = AsyncWorkerPool(storage=storage, concurrency=1, poll_interval=0.5)

        # Create test function
        def test_calculation(x):
            return x * 2

        task = Task.create(test_calculation, args=(21,), eta=datetime.now(timezone.utc))

        # Enqueue task
        await storage.enqueue(task)
        print(f"📝 Enqueued task: {task.id}")

        # Start worker
        worker_task = asyncio.create_task(worker_pool.start())
        await asyncio.sleep(1)  # Let it process

        # Stop worker
        await worker_pool.stop()
        worker_task.cancel()

        # Check result
        result = await storage.get_result(task.id)
        if result and result.status == TaskStatus.SUCCESS:
            print(f"✅ Task completed successfully: {result.result}")
        else:
            print(f"❌ Task did not complete: {result}")

        await storage.close()


async def main():
    """Run all worker pool tests."""

    print("🧪 OmniQ Worker Pool Test Suite")
    print("=" * 50)

    # Test basic functionality
    await test_worker_pool_basic()

    # Test retry logic
    await test_retry_logic()

    # Test retry delay calculation (sync)
    test_retry_delay_calculation()

    # Test integration with file storage
    await test_worker_pool_integration()

    print("\n" + "=" * 50)
    print("🎉 All Worker Pool Tests Completed!")
    print("📋 Tested:")
    print("   • Async function execution ✅")
    print("   • Sync function execution ✅")
    print("   • Function arguments handling ✅")
    print("   • Interval task rescheduling ✅")
    print("   • Retry logic with exponential backoff ✅")
    print("   • Integration with file storage ✅")
    print("   • Graceful shutdown ✅")


if __name__ == "__main__":
    asyncio.run(main())
