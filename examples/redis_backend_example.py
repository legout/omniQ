"""
Redis Backend Example for OmniQ.

This example demonstrates how to use the Redis backend for task queue,
result storage, and event storage with OmniQ.
"""

import asyncio
from datetime import datetime, timedelta

from omniq.models.config import RedisConfig
from omniq.backend.redis import AsyncRedisBackend, RedisBackend
from omniq.models.task import Task, TaskStatus
from omniq.models.result import TaskResult, ResultStatus
from omniq.models.event import TaskEvent, EventType


async def async_redis_example():
    """Demonstrate async Redis backend usage."""
    print("=== Async Redis Backend Example ===")
    
    # Create Redis configuration
    config = RedisConfig(
        host="localhost",
        port=6379,
        database=0,
        tasks_prefix="example:tasks",
        results_prefix="example:results",
        events_prefix="example:events"
    )
    
    # Create async Redis backend
    async with AsyncRedisBackend(config) as backend:
        print(f"Connected to Redis at {config.host}:{config.port}")
        
        # Health check
        health = await backend.health_check()
        print(f"Health check: {health['status']}")
        
        # Create a sample task
        task = Task(
            id="task-001",
            func="example_function",
            args=(1, 2, 3),
            kwargs={"key": "value"},
            queue_name="default",
            priority=1,
            status=TaskStatus.PENDING,
            run_at=datetime.utcnow()
        )
        
        # Enqueue task
        task_id = await backend.queue.enqueue(task)
        print(f"Enqueued task: {task_id}")
        
        # Get queue size
        queue_size = await backend.queue.get_queue_size("default")
        print(f"Queue size: {queue_size}")
        
        # Dequeue task
        dequeued_task = await backend.queue.dequeue(["default"], timeout=1.0)
        if dequeued_task:
            print(f"Dequeued task: {dequeued_task.id}")
            
            # Create and store result
            result = TaskResult(
                task_id=dequeued_task.id,
                status=ResultStatus.SUCCESS,
                result={"output": "Task completed successfully"},
                created_at=datetime.utcnow(),
                ttl=timedelta(hours=24)
            )
            
            await backend.result_storage.set(result)
            print(f"Stored result for task: {result.task_id}")
            
            # Retrieve result
            retrieved_result = await backend.result_storage.get(dequeued_task.id)
            if retrieved_result:
                print(f"Retrieved result: {retrieved_result.result}")
            
            # Log event
            event = TaskEvent(
                id="event-001",
                task_id=dequeued_task.id,
                event_type=EventType.COMPLETED,
                details={"duration": 1.5, "worker": "worker-001"},
                timestamp=datetime.utcnow()
            )
            
            await backend.event_storage.log_event(event)
            print(f"Logged event: {event.event_type}")
            
            # Get events
            events = await backend.event_storage.get_events(
                task_id=dequeued_task.id,
                limit=10
            )
            print(f"Found {len(events)} events for task")
        
        # Cleanup
        cleanup_stats = await backend.cleanup()
        print(f"Cleanup completed: {cleanup_stats}")


def sync_redis_example():
    """Demonstrate sync Redis backend usage."""
    print("\n=== Sync Redis Backend Example ===")
    
    # Create Redis configuration
    config = RedisConfig(
        host="localhost",
        port=6379,
        database=1,  # Use different database
        tasks_prefix="sync:tasks",
        results_prefix="sync:results",
        events_prefix="sync:events"
    )
    
    # Create sync Redis backend
    with RedisBackend(config) as backend:
        print(f"Connected to Redis at {config.host}:{config.port}")
        
        # Health check
        health = backend.health_check_sync()
        print(f"Health check: {health['status']}")
        
        # Create a sample task
        task = Task(
            id="sync-task-001",
            func="sync_example_function",
            args=("hello", "world"),
            kwargs={"sync": True},
            queue_name="sync_queue",
            priority=2,
            status=TaskStatus.PENDING,
            run_at=datetime.utcnow()
        )
        
        # Enqueue task
        task_id = backend.queue.enqueue_sync(task)
        print(f"Enqueued sync task: {task_id}")
        
        # List tasks
        tasks = backend.queue.list_tasks_sync(queue_name="sync_queue", limit=5)
        print(f"Found {len(tasks)} tasks in sync_queue")
        
        # Get queue size
        queue_size = backend.queue.get_queue_size_sync("sync_queue")
        print(f"Sync queue size: {queue_size}")
        
        # Cleanup
        cleanup_stats = backend.cleanup_sync()
        print(f"Sync cleanup completed: {cleanup_stats}")


async def redis_transaction_example():
    """Demonstrate Redis transaction usage."""
    print("\n=== Redis Transaction Example ===")
    
    config = RedisConfig(
        host="localhost",
        port=6379,
        database=2,
        tasks_prefix="tx:tasks",
        results_prefix="tx:results",
        events_prefix="tx:events"
    )
    
    async with AsyncRedisBackend(config) as backend:
        # Use transaction context manager
        async with backend.transaction():
            # Create multiple tasks
            tasks = []
            for i in range(3):
                task = Task(
                    id=f"tx-task-{i:03d}",
                    func="batch_function",
                    args=(i,),
                    kwargs={"batch": True},
                    queue_name="batch_queue",
                    priority=1,
                    status=TaskStatus.PENDING,
                    run_at=datetime.utcnow()
                )
                tasks.append(task)
                await backend.queue.enqueue(task)
            
            print(f"Enqueued {len(tasks)} tasks in transaction")
        
        # Check queue size
        queue_size = await backend.queue.get_queue_size("batch_queue")
        print(f"Batch queue size after transaction: {queue_size}")


async def main():
    """Run all Redis backend examples."""
    try:
        await async_redis_example()
        sync_redis_example()
        await redis_transaction_example()
        
        print("\n=== Redis Backend Examples Completed ===")
        print("Note: Make sure Redis server is running on localhost:6379")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure Redis server is running and accessible")


if __name__ == "__main__":
    asyncio.run(main())