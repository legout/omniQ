"""Backend-Based Usage Examples for OmniQ.

This module demonstrates how to use the backend abstraction layer to simplify
OmniQ configuration. Backends act as unified factories for creating storage
components, reducing configuration complexity while maintaining flexibility.

The examples show:
1. Single backend usage - all components use the same backend
2. Mixed backend usage - different backends for different components
3. Individual component creation from backends
"""

import asyncio
import datetime as dt
from pathlib import Path

from omniq import OmniQ, AsyncOmniQ
from omniq.backend import SQLiteBackend
from omniq.queue import TaskQueue
from omniq.results import ResultStore
from omniq.events import EventStore


def simple_task(name: str, multiplier: int = 1) -> str:
    """A simple task function for demonstration."""
    result = f"Hello {name}!" * multiplier
    print(f"Task executed: {result}")
    return result


async def async_task(name: str, delay: float = 0.1) -> str:
    """An async task function for demonstration."""
    await asyncio.sleep(delay)
    result = f"Async hello {name}!"
    print(f"Async task executed: {result}")
    return result


def single_backend_example():
    """Demonstrate using a single backend for all components.
    
    This is the simplest backend-based approach where all storage components
    (queue, result storage, event storage) use the same backend configuration.
    """
    print("=== Single Backend Example ===")
    
    # Create a SQLite backend - all components will use this database
    sqlite_backend = SQLiteBackend({
        "db_path": "examples/03_backend_based_usage/single_backend.db",
        "create_dirs": True
    })
    
    # Create OmniQ instance from the backend
    # All components (queue, result storage, event storage) will use SQLite
    oq = OmniQ.from_backend(
        backend=sqlite_backend,
        worker_type="thread_pool",
        worker_config={"max_workers": 4}
    )
    
    print(f"Created OmniQ with SQLite backend: {sqlite_backend}")
    
    # Use the OmniQ instance
    with oq:
        # Start the worker
        oq.start_worker()
        
        # Enqueue some tasks
        task_id1 = oq.enqueue(
            func=simple_task,
            func_kwargs={"name": "Alice", "multiplier": 2},
            queue_name="default"
        )
        
        task_id2 = oq.enqueue(
            func=simple_task,
            func_kwargs={"name": "Bob", "multiplier": 1},
            queue_name="default",
            run_in=dt.timedelta(seconds=1)
        )
        
        print(f"Enqueued tasks: {task_id1}, {task_id2}")
        
        # Wait for results
        result1 = oq.get_result(task_id1, timeout=dt.timedelta(seconds=10))
        result2 = oq.get_result(task_id2, timeout=dt.timedelta(seconds=10))
        
        print(f"Task 1 result: {result1.result if result1 else 'None'}")
        print(f"Task 2 result: {result2.result if result2 else 'None'}")
        
        # Stop the worker
        oq.stop_worker()
    
    print("Single backend example completed.\n")


def mixed_backend_example():
    """Demonstrate using different backends for different components.
    
    This approach allows you to optimize each component by choosing the most
    appropriate backend for its specific requirements.
    """
    print("=== Mixed Backend Example ===")
    
    # Create different backends for different purposes
    
    # Fast file-based backend for task queue (temporary storage)
    file_backend = FileBackend({
        "base_dir": "examples/03_backend_based_usage/queue_storage",
        "create_dirs": True
    })
    
    # Persistent SQLite backend for result storage (long-term storage)
    sqlite_backend = SQLiteBackend({
        "db_path": "examples/03_backend_based_usage/results.db",
        "create_dirs": True
    })
    
    # Another SQLite backend for event storage (audit trail)
    event_backend = SQLiteBackend({
        "db_path": "examples/03_backend_based_usage/events.db",
        "create_dirs": True
    })
    
    print(f"File backend for queue: {file_backend}")
    print(f"SQLite backend for results: {sqlite_backend}")
    print(f"SQLite backend for events: {event_backend}")
    
    # Create OmniQ with mixed backends
    oq = OmniQ.from_backend(
        backend=file_backend,              # Task queue uses file storage
        result_store_backend=sqlite_backend,  # Results use SQLite
        event_store_backend=event_backend,    # Events use separate SQLite DB
        worker_type="async",
        worker_config={"max_workers": 6}
    )
    
    # Use the OmniQ instance
    with oq:
        # Start the worker
        oq.start_worker()
        
        # Enqueue tasks to different queues
        high_priority_task = oq.enqueue(
            func=simple_task,
            func_kwargs={"name": "Priority User", "multiplier": 3},
            queue_name="high"
        )
        
        normal_task = oq.enqueue(
            func=simple_task,
            func_kwargs={"name": "Normal User", "multiplier": 1},
            queue_name="default"
        )
        
        print(f"Enqueued high priority task: {high_priority_task}")
        print(f"Enqueued normal task: {normal_task}")
        
        # Wait for results
        high_result = oq.get_result(high_priority_task, timeout=dt.timedelta(seconds=10))
        normal_result = oq.get_result(normal_task, timeout=dt.timedelta(seconds=10))
        
        print(f"High priority result: {high_result.result if high_result else 'None'}")
        print(f"Normal result: {normal_result.result if normal_result else 'None'}")
        
        # Stop the worker
        oq.stop_worker()
    
    print("Mixed backend example completed.\n")


def component_creation_example():
    """Demonstrate creating individual components from backends.
    
    This approach gives you direct access to individual components while
    still benefiting from backend configuration simplification.
    """
    print("=== Component Creation Example ===")
    
    # Create backends
    sqlite_backend = SQLiteBackend({
        "db_path": "examples/03_backend_based_usage/components.db",
        "create_dirs": True
    })
    
    # Create individual components from the backend
    task_queue = TaskQueue.from_backend(
        backend=sqlite_backend,
        queues=["high", "medium", "low"]
    )
    
    result_store = ResultStore.from_backend(sqlite_backend)
    event_store = EventStore.from_backend(sqlite_backend)
    
    print(f"Created task queue: {task_queue}")
    print(f"Created result store: {result_store}")
    print(f"Created event store: {event_store}")
    
    # Use components directly
    with task_queue, result_store, event_store:
        # Enqueue a task directly to the queue
        task_id = task_queue.enqueue(
            func=simple_task,
            func_kwargs={"name": "Component User", "multiplier": 2},
            queue_name="medium"
        )
        
        print(f"Enqueued task directly to queue: {task_id}")
        
        # Check queue size
        queue_size = task_queue.get_queue_size("medium")
        print(f"Queue 'medium' size: {queue_size}")
        
        # List all queues
        queues = task_queue.list_queues()
        print(f"Available queues: {queues}")
        
        # Note: In a real application, you would also create and start a worker
        # to process the enqueued tasks and store results in the result_store
    
    print("Component creation example completed.\n")


async def async_backend_example():
    """Demonstrate async backend usage.
    
    Shows how to use backends with AsyncOmniQ for high-performance
    asynchronous task processing.
    """
    print("=== Async Backend Example ===")
    
    # Create backend
    sqlite_backend = SQLiteBackend({
        "db_path": "examples/03_backend_based_usage/async_backend.db",
        "create_dirs": True
    })
    
    # Create AsyncOmniQ instance from backend
    async_oq = await AsyncOmniQ.from_backend(
        backend=sqlite_backend,
        worker_type="async",
        worker_config={"max_workers": 8}
    )
    
    print(f"Created AsyncOmniQ with backend: {sqlite_backend}")
    
    # Use the AsyncOmniQ instance
    async with async_oq:
        # Start the worker
        await async_oq.start_worker()
        
        # Enqueue async tasks
        async_task_id = await async_oq.enqueue(
            func=async_task,
            func_kwargs={"name": "Async User", "delay": 0.5},
            queue_name="default"
        )
        
        sync_task_id = await async_oq.enqueue(
            func=simple_task,
            func_kwargs={"name": "Mixed User", "multiplier": 2},
            queue_name="default"
        )
        
        print(f"Enqueued async task: {async_task_id}")
        print(f"Enqueued sync task: {sync_task_id}")
        
        # Wait for results
        async_result = await async_oq.get_result(
            async_task_id, 
            timeout=dt.timedelta(seconds=10)
        )
        sync_result = await async_oq.get_result(
            sync_task_id, 
            timeout=dt.timedelta(seconds=10)
        )
        
        print(f"Async task result: {async_result.result if async_result else 'None'}")
        print(f"Sync task result: {sync_result.result if sync_result else 'None'}")
        
        # Stop the worker
        await async_oq.stop_worker()
    
    print("Async backend example completed.\n")


def cleanup_example_files():
    """Clean up example database files."""
    print("=== Cleanup ===")
    
    example_files = [
        "examples/03_backend_based_usage/single_backend.db",
        "examples/03_backend_based_usage/results.db",
        "examples/03_backend_based_usage/events.db",
        "examples/03_backend_based_usage/components.db",
        "examples/03_backend_based_usage/async_backend.db"
    ]
    
    for file_path in example_files:
        try:
            Path(file_path).unlink(missing_ok=True)
            print(f"Cleaned up: {file_path}")
        except Exception as e:
            print(f"Could not clean up {file_path}: {e}")
    
    # Clean up queue storage directory
    import shutil
    try:
        shutil.rmtree("examples/03_backend_based_usage/queue_storage", ignore_errors=True)
        print("Cleaned up: queue_storage directory")
    except Exception as e:
        print(f"Could not clean up queue_storage: {e}")


def main():
    """Run all backend-based usage examples."""
    print("Backend-Based Usage Examples for OmniQ")
    print("=" * 50)
    
    # Ensure the example directory exists
    Path("examples/03_backend_based_usage").mkdir(parents=True, exist_ok=True)
    
    try:
        # Run synchronous examples
        single_backend_example()
        mixed_backend_example()
        component_creation_example()
        
        # Run async example
        asyncio.run(async_backend_example())
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up example files
        cleanup_example_files()
    
    print("All backend-based usage examples completed!")


if __name__ == "__main__":
    main()