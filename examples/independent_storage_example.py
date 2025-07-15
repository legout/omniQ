"""
Example demonstrating independent storage backend selection in OmniQ.

This example shows how to configure different storage backends for different
components (task queue, result storage, event storage, schedule storage).
"""

import asyncio
import os
from datetime import datetime, timedelta

from omniq import OmniQ
from omniq.models.config import OmniQConfig, StorageBackendConfig
from omniq.models.schedule import ScheduleType


async def main():
    """Demonstrate independent storage backend configuration."""
    
    # Example 1: Using environment variables for configuration
    print("=== Example 1: Environment Variable Configuration ===")
    
    # Set environment variables for different storage backends
    os.environ["OMNIQ_TASK_QUEUE_TYPE"] = "sqlite"
    os.environ["OMNIQ_TASK_QUEUE_URL"] = "sqlite:///tasks.db"
    
    os.environ["OMNIQ_RESULT_STORAGE_TYPE"] = "file"
    os.environ["OMNIQ_RESULT_STORAGE_URL"] = "./results"
    
    os.environ["OMNIQ_EVENT_STORAGE_TYPE"] = "memory"
    
    os.environ["OMNIQ_SCHEDULE_STORAGE_TYPE"] = "sqlite"
    os.environ["OMNIQ_SCHEDULE_STORAGE_URL"] = "sqlite:///schedules.db"
    
    # Create OmniQ instance with environment-based configuration
    omniq_env = OmniQ()
    
    async with omniq_env:
        # Submit a task
        task_id = await omniq_env.submit_task(
            func_name="example_task",
            args=("Hello", "World"),
            kwargs={"priority": "high"}
        )
        print(f"Task submitted with ID: {task_id}")
        
        # Get task details
        task = await omniq_env.get_task(task_id)
        if task:
            print(f"Task details: {task.func} with args {task.args}")
        else:
            print("Task not found")
    
    print()
    
    # Example 2: Using programmatic configuration
    print("=== Example 2: Programmatic Configuration ===")
    
    # Create configuration with different backends for each component
    config = OmniQConfig(
        project_name="mixed_storage_example",
        
        # Task queue uses SQLite
        task_queue_backend=StorageBackendConfig(
            backend_type="sqlite",
            url="sqlite:///task_queue.db"
        ),
        
        # Result storage uses file system
        result_storage_backend=StorageBackendConfig(
            backend_type="file",
            config={
                "base_dir": "./results_data",
                "serialization_format": "json"
            }
        ),
        
        # Event storage uses memory (for fast access)
        event_storage_backend=StorageBackendConfig(
            backend_type="memory"
        ),
        
        # Schedule storage uses SQLite (separate database)
        schedule_storage_backend=StorageBackendConfig(
            backend_type="sqlite",
            url="sqlite:///schedules.db"
        ),
        
        default_ttl=3600,  # 1 hour
        log_level="INFO"
    )
    
    # Create OmniQ instance with programmatic configuration
    omniq_prog = OmniQ(config=config)
    
    async with omniq_prog:
        # Submit multiple tasks
        task_ids = []
        for i in range(3):
            task_id = await omniq_prog.submit_task(
                func_name="batch_task",
                args=(i,),
                kwargs={"batch": True},
                priority=i
            )
            task_ids.append(task_id)
        
        print(f"Submitted {len(task_ids)} tasks: {task_ids}")
        
        # Get tasks by queue
        tasks = await omniq_prog.get_tasks_by_queue("default", limit=10)
        print(f"Found {len(tasks)} tasks in default queue")
        
        # Create a schedule
        schedule_id = await omniq_prog.create_schedule(
            func="scheduled_task",
            schedule_type=ScheduleType.INTERVAL,
            interval=timedelta(minutes=5),
            args=("scheduled",),
            max_runs=10
        )
        print(f"Created schedule with ID: {schedule_id}")
    
    print()
    
    # Example 3: Mixed configuration (some from env, some programmatic)
    print("=== Example 3: Mixed Configuration ===")
    
    # Clear some environment variables
    if "OMNIQ_RESULT_STORAGE_TYPE" in os.environ:
        del os.environ["OMNIQ_RESULT_STORAGE_TYPE"]
    if "OMNIQ_RESULT_STORAGE_URL" in os.environ:
        del os.environ["OMNIQ_RESULT_STORAGE_URL"]
    
    # Create configuration that uses environment for some, explicit for others
    mixed_config = OmniQConfig(
        # Task queue and schedule storage will use environment variables
        # (OMNIQ_TASK_QUEUE_TYPE=sqlite, OMNIQ_SCHEDULE_STORAGE_TYPE=sqlite)
        
        # Explicitly configure result storage
        result_storage_backend=StorageBackendConfig(
            backend_type="memory"  # Use memory for fast results
        ),
        
        # Explicitly configure event storage
        event_storage_backend=StorageBackendConfig(
            backend_type="file",
            config={
                "base_dir": "./events_data",
                "serialization_format": "json"
            }
        ),
        
        log_level="DEBUG"
    )
    
    omniq_mixed = OmniQ(config=mixed_config)
    
    async with omniq_mixed:
        # Submit a task and immediately check for events
        task_id = await omniq_mixed.submit_task(
            func_name="monitored_task",
            args=("monitoring", "example"),
            metadata={"source": "mixed_config_example"}
        )
        
        # Get task events (should be stored in file system)
        events = await omniq_mixed.get_task_events(task_id)
        print(f"Task {task_id} has {len(events)} events")
        for event in events:
            print(f"  - {event.event_type} at {event.timestamp}")
    
    print()
    
    # Example 4: All-memory configuration (for testing/development)
    print("=== Example 4: All-Memory Configuration ===")
    
    memory_config = OmniQConfig(
        project_name="memory_test",
        
        # All components use memory storage
        task_queue_backend=StorageBackendConfig(backend_type="memory"),
        result_storage_backend=StorageBackendConfig(backend_type="memory"),
        event_storage_backend=StorageBackendConfig(backend_type="memory"),
        schedule_storage_backend=StorageBackendConfig(backend_type="memory"),
        
        log_level="WARNING"  # Reduce noise for testing
    )
    
    omniq_memory = OmniQ(config=memory_config)
    
    async with omniq_memory:
        # This configuration is perfect for unit tests or development
        # where you don't want persistent storage
        
        task_id = await omniq_memory.submit_task(
            func_name="test_task",
            args=("fast", "ephemeral"),
            delay=1  # 1 second delay
        )
        
        print(f"Memory-based task submitted: {task_id}")
        
        # Task will be lost when the process ends, which is perfect for testing
        task = await omniq_memory.get_task(task_id)
        print(f"Task status: {task.status if task else 'Not found'}")
    
    print("\n=== All Examples Completed ===")
    print("Each example demonstrated different ways to configure independent storage backends:")
    print("1. Environment variables for all components")
    print("2. Programmatic configuration for all components")
    print("3. Mixed configuration (env + programmatic)")
    print("4. All-memory configuration for testing")


if __name__ == "__main__":
    asyncio.run(main())