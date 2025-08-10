# Task 4: Examples for the Implemented Core and SQLite Backend

## Overview

This task involves creating comprehensive examples that demonstrate the usage of OmniQ's core components and SQLite backend. The examples will cover basic usage, advanced features, and real-world scenarios.

## Objectives

1. Create basic usage examples for OmniQ
2. Create examples for SQLite backend components
3. Create examples for task scheduling and dependencies
4. Create examples for worker types and configurations
5. Create real-world scenario examples

## Detailed Implementation Plan

### 4.1 Example Structure and Organization

**Purpose**: Organize examples in a logical structure that makes them easy to find and understand.

**Implementation Requirements**:
- Create an examples directory with subdirectories for different categories
- Include README files with explanations
- Provide both simple and complex examples
- Include example data files where needed

**Directory Structure**:
```
examples/
├── README.md                     # Overview of all examples
├── basic/                        # Basic usage examples
│   ├── README.md
│   ├── simple_task.py            # Simple task enqueue and result retrieval
│   ├── multiple_tasks.py         # Enqueuing multiple tasks
│   ├── sync_vs_async.py          # Comparison of sync and async usage
│   └── context_manager.py        # Using context managers
├── sqlite_backend/               # SQLite backend specific examples
│   ├── README.md
│   ├── sqlite_setup.py           # Setting up SQLite backend
│   ├── sqlite_queues.py          # Working with SQLite queues
│   ├── sqlite_results.py         # Working with SQLite result storage
│   └── sqlite_events.py          # Working with SQLite event storage
├── scheduling/                   # Task scheduling examples
│   ├── README.md
│   ├── interval_scheduling.py    # Interval-based scheduling
│   ├── cron_scheduling.py        # Cron-based scheduling
│   ├── run_at_scheduling.py      # Run-at scheduling
│   └── schedule_management.py    # Pausing and resuming schedules
├── workers/                      # Worker examples
│   ├── README.md
│   ├── async_worker.py           # Using async workers
│   ├── thread_pool_worker.py     # Using thread pool workers
│   ├── worker_configuration.py   # Configuring workers
│   └── worker_events.py          # Handling worker events
├── advanced/                     # Advanced usage examples
│   ├── README.md
│   ├── task_dependencies.py      # Task dependencies
│   ├── task_chaining.py          # Chaining tasks
│   ├── error_handling.py         # Error handling and retries
│   ├── task_ttl.py               # Task TTL and cleanup
│   └── multiple_queues.py        # Working with multiple queues
├── real_world/                   # Real-world scenario examples
│   ├── README.md
│   ├── data_processing.py        # Data processing pipeline
│   ├── web_scraping.py           # Web scraping with rate limiting
│   ├── email_notifications.py    # Email notification system
│   └── batch_processing.py       # Batch processing system
└── configuration/                # Configuration examples
    ├── README.md
    ├── yaml_config.py            # YAML configuration
    ├── env_config.py             # Environment variable configuration
    ├── programmatic_config.py    # Programmatic configuration
    └── mixed_config.py           # Mixed configuration sources
```

### 4.2 Main Examples README (`examples/README.md`)

**Purpose**: Provide an overview of all examples and how to use them.

**Implementation Requirements**:
- Explain the purpose of the examples
- Provide instructions for running the examples
- Include prerequisites and setup information

**Code Structure**:
```markdown
# OmniQ Examples

This directory contains examples demonstrating how to use OmniQ, a flexible task queue library for Python.

## Prerequisites

Before running the examples, make sure you have:

1. Installed OmniQ and its dependencies:
   ```bash
   pip install -e .
   ```

2. Installed the required dependencies for the examples:
   ```bash
   pip install aiosqlite
   ```

## Running the Examples

Most examples can be run directly with Python:

```bash
python basic/simple_task.py
```

Some examples may require additional setup or dependencies, which are noted in their respective README files.

## Example Categories

### Basic Usage (`basic/`)

These examples demonstrate the fundamental usage of OmniQ:

- `simple_task.py`: Enqueue a simple task and retrieve its result
- `multiple_tasks.py`: Enqueue and process multiple tasks
- `sync_vs_async.py`: Compare synchronous and asynchronous usage
- `context_manager.py`: Use context managers for resource management

### SQLite Backend (`sqlite_backend/`)

These examples show how to use the SQLite backend:

- `sqlite_setup.py`: Set up a SQLite backend
- `sqlite_queues.py`: Work with SQLite-based task queues
- `sqlite_results.py`: Store and retrieve results using SQLite
- `sqlite_events.py`: Log and query events using SQLite

### Task Scheduling (`scheduling/`)

These examples demonstrate task scheduling features:

- `interval_scheduling.py`: Schedule tasks to run at regular intervals
- `cron_scheduling.py`: Schedule tasks using cron expressions
- `run_at_scheduling.py`: Schedule tasks to run at specific times
- `schedule_management.py`: Pause and resume scheduled tasks

### Workers (`workers/`)

These examples show different worker configurations:

- `async_worker.py`: Use async workers for I/O-bound tasks
- `thread_pool_worker.py`: Use thread pool workers for CPU-bound tasks
- `worker_configuration.py`: Configure worker settings
- `worker_events.py`: Handle worker events and callbacks

### Advanced Usage (`advanced/`)

These examples cover advanced features:

- `task_dependencies.py`: Define and use task dependencies
- `task_chaining.py`: Chain tasks together
- `error_handling.py`: Handle errors and retries
- `task_ttl.py`: Use task TTL for automatic cleanup
- `multiple_queues.py`: Work with multiple named queues

### Real-World Scenarios (`real_world/`)

These examples demonstrate real-world use cases:

- `data_processing.py`: Implement a data processing pipeline
- `web_scraping.py`: Build a web scraping system with rate limiting
- `email_notifications.py`: Create an email notification system
- `batch_processing.py`: Implement a batch processing system

### Configuration (`configuration/`)

These examples show different ways to configure OmniQ:

- `yaml_config.py`: Configure OmniQ using YAML files
- `env_config.py`: Configure OmniQ using environment variables
- `programmatic_config.py`: Configure OmniQ programmatically
- `mixed_config.py`: Use multiple configuration sources

## Tips for Learning

1. **Start with the basics**: Begin with the `basic/` examples to understand the core concepts.
2. **Experiment**: Modify the examples to see how changes affect behavior.
3. **Read the code**: Look at the implementation to understand how things work.
4. **Check the logs**: Many examples include logging to help understand what's happening.
5. **Ask questions**: If something is unclear, refer to the main documentation or create an issue.

## Contributing Examples

If you have an example that you think would be helpful for others, please consider contributing it to the OmniQ project. See the main project README for information on how to contribute.
```

### 4.3 Basic Usage Examples

#### 4.3.1 Simple Task Example (`examples/basic/simple_task.py`)

**Purpose**: Demonstrate the most basic usage of OmniQ.

**Implementation Requirements**:
- Show how to create a task
- Show how to enqueue a task
- Show how to retrieve a result
- Include both sync and async examples

**Code Structure**:
```python
# examples/basic/simple_task.py
"""
Simple task example demonstrating basic OmniQ usage.

This example shows how to:
1. Define a simple function to be used as a task
2. Create an OmniQ instance with SQLite backend
3. Enqueue a task
4. Retrieve the result
"""

import asyncio
from omniq import OmniQ

# Define a simple function that will be used as a task
def add_numbers(x, y):
    """Add two numbers and return the result."""
    return x + y

async def async_add_numbers(x, y):
    """Asynchronously add two numbers and return the result."""
    await asyncio.sleep(0.1)  # Simulate async work
    return x + y

def main_sync():
    """Demonstrate synchronous usage of OmniQ."""
    print("=== Synchronous Example ===")
    
    # Create an OmniQ instance with SQLite backend
    with OmniQ(project_name="simple_example", backend_type="sqlite") as oq:
        # Start a worker
        oq.start_worker(worker_type="thread_pool", max_workers=1)
        
        try:
            # Enqueue a task
            print("Enqueuing task...")
            task_id = oq.enqueue(
                func=add_numbers,
                func_args={"x": 5, "y": 10},
                queue_name="default"
            )
            print(f"Task enqueued with ID: {task_id}")
            
            # Get the result
            print("Getting result...")
            result = oq.get_result(task_id)
            print(f"Result: {result}")
            
        finally:
            # Stop the worker
            oq.stop_worker()

async def main_async():
    """Demonstrate asynchronous usage of OmniQ."""
    print("\n=== Asynchronous Example ===")
    
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name="simple_example_async", backend_type="sqlite") as oq:
        # Start a worker
        await oq.start_worker_async(worker_type="async", max_workers=1)
        
        try:
            # Enqueue a task
            print("Enqueuing task...")
            task_id = await oq.enqueue_async(
                func=async_add_numbers,
                func_args={"x": 5, "y": 10},
                queue_name="default"
            )
            print(f"Task enqueued with ID: {task_id}")
            
            # Get the result
            print("Getting result...")
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

if __name__ == "__main__":
    # Run the synchronous example
    main_sync()
    
    # Run the asynchronous example
    asyncio.run(main_async())
```

#### 4.3.2 Multiple Tasks Example (`examples/basic/multiple_tasks.py`)

**Purpose**: Demonstrate enqueuing and processing multiple tasks.

**Implementation Requirements**:
- Show how to enqueue multiple tasks
- Show how to process tasks concurrently
- Show how to retrieve multiple results
- Include progress tracking

**Code Structure**:
```python
# examples/basic/multiple_tasks.py
"""
Multiple tasks example demonstrating concurrent task processing.

This example shows how to:
1. Define multiple tasks
2. Enqueue them concurrently
3. Process them with multiple workers
4. Retrieve all results
"""

import asyncio
import time
from omniq import OmniQ

# Define functions to be used as tasks
def process_data(data_id, processing_time=0.1):
    """Process some data with a simulated delay."""
    time.sleep(processing_time)
    return f"Processed data {data_id}"

async def async_process_data(data_id, processing_time=0.1):
    """Asynchronously process some data with a simulated delay."""
    await asyncio.sleep(processing_time)
    return f"Async processed data {data_id}"

def main_sync():
    """Demonstrate synchronous processing of multiple tasks."""
    print("=== Synchronous Multiple Tasks Example ===")
    
    # Create an OmniQ instance with SQLite backend
    with OmniQ(project_name="multiple_tasks_example", backend_type="sqlite") as oq:
        # Start a worker with multiple threads
        oq.start_worker(worker_type="thread_pool", max_workers=4)
        
        try:
            # Enqueue multiple tasks
            print("Enqueuing 10 tasks...")
            task_ids = []
            for i in range(10):
                task_id = oq.enqueue(
                    func=process_data,
                    func_args={"data_id": i, "processing_time": 0.1},
                    queue_name="default"
                )
                task_ids.append(task_id)
            
            print(f"Enqueued {len(task_ids)} tasks")
            
            # Get all results
            print("Getting all results...")
            results = []
            for task_id in task_ids:
                result = oq.get_result(task_id)
                results.append(result)
                print(f"Task {task_id}: {result}")
            
            print(f"Processed {len(results)} tasks")
            
        finally:
            # Stop the worker
            oq.stop_worker()

async def main_async():
    """Demonstrate asynchronous processing of multiple tasks."""
    print("\n=== Asynchronous Multiple Tasks Example ===")
    
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name="multiple_tasks_example_async", backend_type="sqlite") as oq:
        # Start a worker with multiple async workers
        await oq.start_worker_async(worker_type="async", max_workers=4)
        
        try:
            # Enqueue multiple tasks concurrently
            print("Enqueuing 10 tasks concurrently...")
            enqueue_tasks = [
                oq.enqueue_async(
                    func=async_process_data,
                    func_args={"data_id": i, "processing_time": 0.1},
                    queue_name="default"
                )
                for i in range(10)
            ]
            task_ids = await asyncio.gather(*enqueue_tasks)
            
            print(f"Enqueued {len(task_ids)} tasks")
            
            # Get all results concurrently
            print("Getting all results concurrently...")
            get_result_tasks = [oq.get_result_async(task_id) for task_id in task_ids]
            results = await asyncio.gather(*get_result_tasks)
            
            for task_id, result in zip(task_ids, results):
                print(f"Task {task_id}: {result}")
            
            print(f"Processed {len(results)} tasks")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

async def main_mixed():
    """Demonstrate processing both sync and async tasks."""
    print("\n=== Mixed Sync/Async Tasks Example ===")
    
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name="mixed_tasks_example", backend_type="sqlite") as oq:
        # Start a worker with multiple async workers
        await oq.start_worker_async(worker_type="async", max_workers=4)
        
        try:
            # Enqueue both sync and async tasks
            print("Enqueuing 5 sync and 5 async tasks...")
            task_ids = []
            
            # Enqueue sync tasks
            for i in range(5):
                task_id = await oq.enqueue_async(
                    func=process_data,
                    func_args={"data_id": f"sync-{i}", "processing_time": 0.1},
                    queue_name="default"
                )
                task_ids.append(task_id)
            
            # Enqueue async tasks
            for i in range(5):
                task_id = await oq.enqueue_async(
                    func=async_process_data,
                    func_args={"data_id": f"async-{i}", "processing_time": 0.1},
                    queue_name="default"
                )
                task_ids.append(task_id)
            
            print(f"Enqueued {len(task_ids)} tasks")
            
            # Get all results
            print("Getting all results...")
            results = await asyncio.gather(*[oq.get_result_async(task_id) for task_id in task_ids])
            
            for task_id, result in zip(task_ids, results):
                print(f"Task {task_id}: {result}")
            
            print(f"Processed {len(results)} tasks")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

if __name__ == "__main__":
    # Run the synchronous example
    main_sync()
    
    # Run the asynchronous example
    asyncio.run(main_async())
    
    # Run the mixed example
    asyncio.run(main_mixed())
```

### 4.4 SQLite Backend Examples

#### 4.4.1 SQLite Setup Example (`examples/sqlite_backend/sqlite_setup.py`)

**Purpose**: Demonstrate how to set up and use the SQLite backend.

**Implementation Requirements**:
- Show how to create a SQLite backend
- Show how to configure the backend
- Show how to create components from the backend
- Include both direct and factory-based approaches

**Code Structure**:
```python
# examples/sqlite_backend/sqlite_setup.py
"""
SQLite backend setup example.

This example shows how to:
1. Create a SQLite backend
2. Configure the backend
3. Create components from the backend
4. Use the components directly
"""

import asyncio
import tempfile
from pathlib import Path
from omniq.backends.sqlite import SQLiteBackend
from omniq.backends.factory import (
    create_sqlite_backend,
    create_sqlite_task_queue,
    create_sqlite_result_storage,
    create_sqlite_event_storage,
    create_sqlite_worker
)

def simple_task(x, y):
    """Simple task function."""
    return x + y

def main_direct():
    """Demonstrate direct backend creation and usage."""
    print("=== Direct Backend Creation ===")
    
    # Create a temporary directory for the database
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a SQLite backend
        backend = SQLiteBackend(
            project_name="sqlite_example",
            base_dir=temp_dir
        )
        
        # Initialize the backend
        backend.initialize()
        
        try:
            # Create components from the backend
            task_queue = backend.get_task_queue(["default"])
            result_storage = backend.get_result_storage()
            event_storage = backend.get_event_storage()
            
            # Create a worker
            worker = create_sqlite_worker(
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                max_workers=1
            )
            
            # Start the worker
            worker.start()
            
            try:
                # Enqueue a task
                task_id = task_queue.enqueue(
                    func=simple_task,
                    func_args={"x": 5, "y": 10}
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = result_storage.get(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                worker.stop()
        
        finally:
            # Close the backend
            backend.close()

def main_factory():
    """Demonstrate factory-based backend creation and usage."""
    print("\n=== Factory-Based Backend Creation ===")
    
    # Create a temporary directory for the database
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a SQLite backend using the factory
        backend = create_sqlite_backend(
            project_name="sqlite_factory_example",
            base_dir=temp_dir
        )
        
        # Initialize the backend
        backend.initialize()
        
        try:
            # Create components using factory functions
            task_queue = create_sqlite_task_queue(backend, ["default"])
            result_storage = create_sqlite_result_storage(backend)
            event_storage = create_sqlite_event_storage(backend)
            
            # Create a worker using the factory
            worker = create_sqlite_worker(
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                max_workers=1
            )
            
            # Start the worker
            worker.start()
            
            try:
                # Enqueue a task
                task_id = task_queue.enqueue(
                    func=simple_task,
                    func_args={"x": 7, "y": 3}
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = result_storage.get(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                worker.stop()
        
        finally:
            # Close the backend
            backend.close()

async def main_direct_async():
    """Demonstrate direct async backend creation and usage."""
    print("\n=== Direct Async Backend Creation ===")
    
    # Create a temporary directory for the database
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a SQLite backend
        backend = SQLiteBackend(
            project_name="sqlite_async_example",
            base_dir=temp_dir
        )
        
        # Initialize the backend
        await backend.initialize_async()
        
        try:
            # Create components from the backend
            task_queue = backend.get_task_queue(["default"])
            result_storage = backend.get_result_storage()
            event_storage = backend.get_event_storage()
            
            # Create a worker
            worker = create_sqlite_worker(
                task_queue=task_queue,
                result_storage=result_storage,
                event_storage=event_storage,
                max_workers=1
            )
            
            # Start the worker
            await worker.start_async()
            
            try:
                # Enqueue a task
                task_id = await task_queue.enqueue_async(
                    func=simple_task,
                    func_args={"x": 8, "y": 2}
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = await result_storage.get_async(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                await worker.stop_async()
        
        finally:
            # Close the backend
            await backend.close_async()

def main_config_based():
    """Demonstrate configuration-based backend creation."""
    print("\n=== Configuration-Based Backend Creation ===")
    
    # Create a temporary directory for the database
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a configuration dictionary
        config = {
            "project_name": "sqlite_config_example",
            "task_queue": {
                "type": "sqlite",
                "config": {
                    "base_dir": temp_dir,
                    "queues": ["high", "medium", "low"]
                }
            },
            "result_store": {
                "type": "sqlite",
                "config": {
                    "base_dir": temp_dir
                }
            },
            "event_store": {
                "type": "sqlite",
                "config": {
                    "base_dir": temp_dir
                }
            },
            "worker": {
                "type": "thread_pool",
                "config": {
                    "max_workers": 2
                }
            }
        }
        
        # Create components from the configuration
        from omniq.backends.factory import create_sqlite_components_from_config
        components = create_sqlite_components_from_config(config)
        
        # Extract components
        backend = components["backend"]
        task_queue = components["task_queue"]
        result_storage = components["result_storage"]
        event_storage = components["event_storage"]
        worker = components["worker"]
        
        # Initialize the backend
        backend.initialize()
        
        try:
            # Start the worker
            worker.start()
            
            try:
                # Enqueue a task to the high priority queue
                task_id = task_queue.enqueue(
                    func=simple_task,
                    func_args={"x": 9, "y": 1},
                    queue_name="high"
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = result_storage.get(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                worker.stop()
        
        finally:
            # Close the backend
            backend.close()

if __name__ == "__main__":
    # Run the direct example
    main_direct()
    
    # Run the factory example
    main_factory()
    
    # Run the async example
    asyncio.run(main_direct_async())
    
    # Run the config-based example
    main_config_based()
```

#### 4.4.2 SQLite Queues Example (`examples/sqlite_backend/sqlite_queues.py`)

**Purpose**: Demonstrate working with SQLite-based task queues.

**Implementation Requirements**:
- Show how to create and configure queues
- Show how to work with multiple named queues
- Show priority-based task processing
- Include queue statistics and monitoring

**Code Structure**:
```python
# examples/sqlite_backend/sqlite_queues.py
"""
SQLite queues example.

This example shows how to:
1. Create and configure SQLite task queues
2. Work with multiple named queues
3. Use priority-based task processing
4. Monitor queue statistics
"""

import asyncio
import time
from datetime import datetime, timedelta
from omniq.backends.sqlite import SQLiteBackend
from omniq.backends.factory import create_sqlite_worker

def process_task(task_name, processing_time=0.1):
    """Process a task with a simulated delay."""
    time.sleep(processing_time)
    return f"Processed {task_name}"

def main_single_queue():
    """Demonstrate using a single queue."""
    print("=== Single Queue Example ===")
    
    # Create a SQLite backend
    backend = SQLiteBackend(project_name="single_queue_example")
    backend.initialize()
    
    try:
        # Create a task queue
        task_queue = backend.get_task_queue(["default"])
        
        # Create result and event storage
        result_storage = backend.get_result_storage()
        event_storage = backend.get_event_storage()
        
        # Create a worker
        worker = create_sqlite_worker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            max_workers=2
        )
        
        # Start the worker
        worker.start()
        
        try:
            # Enqueue multiple tasks
            print("Enqueuing 5 tasks...")
            task_ids = []
            for i in range(5):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"Task-{i}", "processing_time": 0.1}
                )
                task_ids.append(task_id)
            
            print(f"Enqueued {len(task_ids)} tasks")
            
            # Get queue stats
            stats = task_queue.get_stats()
            print(f"Queue stats: {stats}")
            
            # Get all results
            results = []
            for task_id in task_ids:
                result = result_storage.get(task_id)
                results.append(result)
                print(f"Task {task_id}: {result}")
            
            # Get final queue stats
            stats = task_queue.get_stats()
            print(f"Final queue stats: {stats}")
            
        finally:
            # Stop the worker
            worker.stop()
    
    finally:
        # Close the backend
        backend.close()

def main_multiple_queues():
    """Demonstrate using multiple named queues."""
    print("\n=== Multiple Queues Example ===")
    
    # Create a SQLite backend
    backend = SQLiteBackend(project_name="multiple_queues_example")
    backend.initialize()
    
    try:
        # Create a task queue with multiple named queues
        task_queue = backend.get_task_queue(["high", "medium", "low"])
        
        # Create result and event storage
        result_storage = backend.get_result_storage()
        event_storage = backend.get_event_storage()
        
        # Create a worker
        worker = create_sqlite_worker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            max_workers=1
        )
        
        # Start the worker
        worker.start()
        
        try:
            # Enqueue tasks to different queues
            print("Enqueuing tasks to different queues...")
            
            # High priority tasks
            high_task_ids = []
            for i in range(2):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"High-{i}", "processing_time": 0.1},
                    queue_name="high"
                )
                high_task_ids.append(task_id)
            
            # Medium priority tasks
            medium_task_ids = []
            for i in range(3):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"Medium-{i}", "processing_time": 0.1},
                    queue_name="medium"
                )
                medium_task_ids.append(task_id)
            
            # Low priority tasks
            low_task_ids = []
            for i in range(4):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"Low-{i}", "processing_time": 0.1},
                    queue_name="low"
                )
                low_task_ids.append(task_id)
            
            print(f"Enqueued {len(high_task_ids)} high, {len(medium_task_ids)} medium, and {len(low_task_ids)} low priority tasks")
            
            # Get queue stats
            stats = task_queue.get_stats()
            print(f"Queue stats: {stats}")
            
            # Get all results
            all_task_ids = high_task_ids + medium_task_ids + low_task_ids
            results = []
            for task_id in all_task_ids:
                result = result_storage.get(task_id)
                results.append(result)
                print(f"Task {task_id}: {result}")
            
            # Get final queue stats
            stats = task_queue.get_stats()
            print(f"Final queue stats: {stats}")
            
        finally:
            # Stop the worker
            worker.stop()
    
    finally:
        # Close the backend
        backend.close()

def main_priority_processing():
    """Demonstrate priority-based task processing."""
    print("\n=== Priority Processing Example ===")
    
    # Create a SQLite backend
    backend = SQLiteBackend(project_name="priority_example")
    backend.initialize()
    
    try:
        # Create a task queue with a single queue
        task_queue = backend.get_task_queue(["default"])
        
        # Create result and event storage
        result_storage = backend.get_result_storage()
        event_storage = backend.get_event_storage()
        
        # Create a worker
        worker = create_sqlite_worker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            max_workers=1
        )
        
        # Start the worker
        worker.start()
        
        try:
            # Enqueue tasks with different priorities
            print("Enqueuing tasks with different priorities...")
            
            # Low priority tasks (enqueue first)
            low_task_ids = []
            for i in range(3):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"Low-{i}", "processing_time": 0.1},
                    priority=1
                )
                low_task_ids.append(task_id)
            
            # Medium priority tasks (enqueue second)
            medium_task_ids = []
            for i in range(2):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"Medium-{i}", "processing_time": 0.1},
                    priority=5
                )
                medium_task_ids.append(task_id)
            
            # High priority tasks (enqueue last)
            high_task_ids = []
            for i in range(1):
                task_id = task_queue.enqueue(
                    func=process_task,
                    func_args={"task_name": f"High-{i}", "processing_time": 0.1},
                    priority=10
                )
                high_task_ids.append(task_id)
            
            print(f"Enqueued {len(low_task_ids)} low, {len(medium_task_ids)} medium, and {len(high_task_ids)} high priority tasks")
            
            # Get all results
            all_task_ids = low_task_ids + medium_task_ids + high_task_ids
            results = []
            for task_id in all_task_ids:
                result = result_storage.get(task_id)
                results.append(result)
                print(f"Task {task_id}: {result}")
            
            # Note: High priority tasks should be processed first, even though they were enqueued last
            
        finally:
            # Stop the worker
            worker.stop()
    
    finally:
        # Close the backend
        backend.close()

async def main_scheduled_tasks():
    """Demonstrate scheduled tasks with SQLite queues."""
    print("\n=== Scheduled Tasks Example ===")
    
    # Create a SQLite backend
    backend = SQLiteBackend(project_name="scheduled_example")
    await backend.initialize_async()
    
    try:
        # Create a task queue
        task_queue = backend.get_task_queue(["default"])
        
        # Create result and event storage
        result_storage = backend.get_result_storage()
        event_storage = backend.get_event_storage()
        
        # Create a worker
        worker = create_sqlite_worker(
            task_queue=task_queue,
            result_storage=result_storage,
            event_storage=event_storage,
            max_workers=1
        )
        
        # Start the worker
        await worker.start_async()
        
        try:
            # Enqueue a task to run in the future
            print("Enqueuing a task to run in 2 seconds...")
            run_at = datetime.utcnow() + timedelta(seconds=2)
            task_id = task_queue.enqueue(
                func=process_task,
                func_args={"task_name": "Future-Task", "processing_time": 0.1},
                run_at=run_at
            )
            
            print(f"Enqueued task with ID: {task_id} to run at {run_at}")
            
            # Schedule a recurring task
            print("Scheduling a recurring task to run every 3 seconds...")
            schedule_id = task_queue.schedule(
                func=process_task,
                func_args={"task_name": "Recurring-Task", "processing_time": 0.1},
                interval=timedelta(seconds=3),
                max_runs=3
            )
            
            print(f"Scheduled task with ID: {schedule_id}")
            
            # Wait for tasks to complete
            print("Waiting for tasks to complete...")
            await asyncio.sleep(10)  # Wait for all tasks to complete
            
            # Get the result of the future task
            result = await result_storage.get_async(task_id)
            print(f"Future task result: {result}")
            
            # Get the results of the scheduled tasks
            schedule_results = await result_storage.get_async(schedule_id=schedule_id, kind="all")
            print(f"Schedule results count: {len(schedule_results)}")
            for i, result in enumerate(schedule_results):
                print(f"Schedule run {i+1}: {result}")
            
        finally:
            # Stop the worker
            await worker.stop_async()
    
    finally:
        # Close the backend
        await backend.close_async()

if __name__ == "__main__":
    # Run the single queue example
    main_single_queue()
    
    # Run the multiple queues example
    main_multiple_queues()
    
    # Run the priority processing example
    main_priority_processing()
    
    # Run the scheduled tasks example
    asyncio.run(main_scheduled_tasks())
```

### 4.5 Real-World Scenario Examples

#### 4.5.1 Data Processing Pipeline Example (`examples/real_world/data_processing.py`)

**Purpose**: Demonstrate a real-world data processing pipeline using OmniQ.

**Implementation Requirements**:
- Show how to build a data processing pipeline
- Show how to chain tasks together
- Show how to handle errors and retries
- Include progress tracking and reporting

**Code Structure**:
```python
# examples/real_world/data_processing.py
"""
Data processing pipeline example.

This example shows how to:
1. Build a data processing pipeline with OmniQ
2. Chain tasks together
3. Handle errors and retries
4. Track progress and report results
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from omniq import OmniQ

# Simulated data processing functions
def extract_data(source_id, batch_size=100):
    """Extract data from a source."""
    # Simulate data extraction
    print(f"Extracting data from source {source_id}...")
    
    # Simulate occasional failures
    if random.random() < 0.1:  # 10% chance of failure
        raise Exception(f"Failed to extract data from source {source_id}")
    
    # Generate sample data
    data = []
    for i in range(batch_size):
        data.append({
            "id": f"{source_id}-{i}",
            "value": random.randint(1, 100),
            "category": random.choice(["A", "B", "C", "D"])
        })
    
    print(f"Extracted {len(data)} records from source {source_id}")
    return data

def transform_data(data, transformation_type="normalize"):
    """Transform data based on the specified type."""
    print(f"Transforming {len(data)} records using {transformation_type}...")
    
    # Simulate occasional failures
    if random.random() < 0.05:  # 5% chance of failure
        raise Exception(f"Failed to transform data using {transformation_type}")
    
    transformed_data = []
    for record in data:
        if transformation_type == "normalize":
            # Normalize values to 0-1 range
            record["normalized_value"] = record["value"] / 100.0
        elif transformation_type == "categorize":
            # Add category based on value
            if record["value"] < 25:
                record["value_category"] = "low"
            elif record["value"] < 75:
                record["value_category"] = "medium"
            else:
                record["value_category"] = "high"
        elif transformation_type == "aggregate":
            # This would typically be done after grouping
            pass
        
        transformed_data.append(record)
    
    print(f"Transformed {len(transformed_data)} records")
    return transformed_data

def load_data(data, destination_id):
    """Load data to a destination."""
    print(f"Loading {len(data)} records to destination {destination_id}...")
    
    # Simulate occasional failures
    if random.random() < 0.05:  # 5% chance of failure
        raise Exception(f"Failed to load data to destination {destination_id}")
    
    # In a real implementation, this would save to a database, file, etc.
    # For this example, we'll just simulate the operation
    time.sleep(0.1)  # Simulate I/O operation
    
    print(f"Loaded {len(data)} records to destination {destination_id}")
    return {"destination": destination_id, "record_count": len(data)}

def generate_report(source_id, destination_id, record_count):
    """Generate a report of the processing job."""
    print(f"Generating report for source {source_id} to destination {destination_id}...")
    
    report = {
        "source_id": source_id,
        "destination_id": destination_id,
        "record_count": record_count,
        "processing_time": random.uniform(1.0, 5.0),  # Simulated
        "timestamp": datetime.utcnow().isoformat(),
        "status": "completed"
    }
    
    # In a real implementation, this would save to a file or database
    print(f"Generated report: {json.dumps(report, indent=2)}")
    return report

async def process_pipeline_async(source_id, destination_id):
    """Process a data pipeline asynchronously."""
    print(f"\n=== Processing pipeline for source {source_id} ===")
    
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name=f"data_pipeline_{source_id}", backend_type="sqlite") as oq:
        # Start a worker
        await oq.start_worker_async(worker_type="async", max_workers=3)
        
        try:
            # Step 1: Extract data
            extract_task_id = await oq.enqueue_async(
                func=extract_data,
                func_args={"source_id": source_id, "batch_size": 100},
                queue_name="extract"
            )
            
            # Step 2: Transform data (depends on extract)
            transform_task_id = await oq.enqueue_async(
                func=transform_data,
                func_args={"data": None, "transformation_type": "normalize"},  # Data will be filled in by the worker
                depends_on=[extract_task_id],
                queue_name="transform"
            )
            
            # Step 3: Load data (depends on transform)
            load_task_id = await oq.enqueue_async(
                func=load_data,
                func_args={"data": None, "destination_id": destination_id},  # Data will be filled in by the worker
                depends_on=[transform_task_id],
                queue_name="load"
            )
            
            # Step 4: Generate report (depends on load)
            report_task_id = await oq.enqueue_async(
                func=generate_report,
                func_args={
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "record_count": None  # Will be filled in by the worker
                },
                depends_on=[load_task_id],
                queue_name="report"
            )
            
            # Wait for the pipeline to complete
            print("Waiting for pipeline to complete...")
            report_result = await oq.get_result_async(report_task_id)
            
            print(f"\nPipeline completed for source {source_id}")
            print(f"Report: {json.dumps(report_result, indent=2)}")
            
            return report_result
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

def process_pipeline_sync(source_id, destination_id):
    """Process a data pipeline synchronously."""
    print(f"\n=== Processing pipeline for source {source_id} (sync) ===")
    
    # Create an OmniQ instance with SQLite backend
    with OmniQ(project_name=f"data_pipeline_sync_{source_id}", backend_type="sqlite") as oq:
        # Start a worker
        oq.start_worker(worker_type="thread_pool", max_workers=3)
        
        try:
            # Step 1: Extract data
            extract_task_id = oq.enqueue(
                func=extract_data,
                func_args={"source_id": source_id, "batch_size": 100},
                queue_name="extract"
            )
            
            # Step 2: Transform data (depends on extract)
            transform_task_id = oq.enqueue(
                func=transform_data,
                func_args={"data": None, "transformation_type": "normalize"},  # Data will be filled in by the worker
                depends_on=[extract_task_id],
                queue_name="transform"
            )
            
            # Step 3: Load data (depends on transform)
            load_task_id = oq.enqueue(
                func=load_data,
                func_args={"data": None, "destination_id": destination_id},  # Data will be filled in by the worker
                depends_on=[transform_task_id],
                queue_name="load"
            )
            
            # Step 4: Generate report (depends on load)
            report_task_id = oq.enqueue(
                func=generate_report,
                func_args={
                    "source_id": source_id,
                    "destination_id": destination_id,
                    "record_count": None  # Will be filled in by the worker
                },
                depends_on=[load_task_id],
                queue_name="report"
            )
            
            # Wait for the pipeline to complete
            print("Waiting for pipeline to complete...")
            report_result = oq.get_result(report_task_id)
            
            print(f"\nPipeline completed for source {source_id}")
            print(f"Report: {json.dumps(report_result, indent=2)}")
            
            return report_result
            
        finally:
            # Stop the worker
            oq.stop_worker()

async def main_multiple_pipelines():
    """Process multiple data pipelines concurrently."""
    print("=== Multiple Data Pipelines Example ===")
    
    # Define sources and destinations
    pipelines = [
        {"source_id": "source-1", "destination_id": "dest-1"},
        {"source_id": "source-2", "destination_id": "dest-2"},
        {"source_id": "source-3", "destination_id": "dest-3"}
    ]
    
    # Process all pipelines concurrently
    pipeline_tasks = [
        process_pipeline_async(pipeline["source_id"], pipeline["destination_id"])
        for pipeline in pipelines
    ]
    
    results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)
    
    # Print results
    print("\n=== Pipeline Results ===")
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Pipeline {i+1} failed: {str(result)}")
        else:
            print(f"Pipeline {i+1} completed successfully")
            print(f"  Records processed: {result.get('record_count', 'Unknown')}")

async def main_scheduled_pipeline():
    """Run a scheduled data processing pipeline."""
    print("\n=== Scheduled Data Pipeline Example ===")
    
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name="scheduled_pipeline", backend_type="sqlite") as oq:
        # Start a worker
        await oq.start_worker_async(worker_type="async", max_workers=3)
        
        try:
            # Schedule a pipeline to run every 30 seconds
            print("Scheduling pipeline to run every 30 seconds...")
            schedule_id = await oq.schedule_async(
                func=process_pipeline_async,
                func_args={"source_id": "scheduled-source", "destination_id": "scheduled-dest"},
                interval=timedelta(seconds=30),
                max_runs=3
            )
            
            print(f"Scheduled pipeline with ID: {schedule_id}")
            
            # Wait for the scheduled runs to complete
            print("Waiting for scheduled runs to complete...")
            await asyncio.sleep(100)  # Wait for all scheduled runs
            
            # Get the results of all scheduled runs
            results = await oq.get_result_async(schedule_id=schedule_id, kind="all")
            
            print(f"\nScheduled pipeline completed {len(results)} runs")
            for i, result in enumerate(results):
                print(f"Run {i+1}: {result.get('record_count', 'Unknown')} records processed")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

if __name__ == "__main__":
    # Run a single synchronous pipeline
    process_pipeline_sync("test-source", "test-dest")
    
    # Run a single asynchronous pipeline
    asyncio.run(process_pipeline_async("test-source-async", "test-dest-async"))
    
    # Run multiple pipelines concurrently
    asyncio.run(main_multiple_pipelines())
    
    # Run a scheduled pipeline
    asyncio.run(main_scheduled_pipeline())
```

### 4.6 Configuration Examples

#### 4.6.1 YAML Configuration Example (`examples/configuration/yaml_config.py`)

**Purpose**: Demonstrate how to configure OmniQ using YAML files.

**Implementation Requirements**:
- Show how to create a YAML configuration file
- Show how to load configuration from YAML
- Show how to use the configuration to create components
- Include different configuration scenarios

**Code Structure**:
```python
# examples/configuration/yaml_config.py
"""
YAML configuration example.

This example shows how to:
1. Create a YAML configuration file
2. Load configuration from YAML
3. Use the configuration to create components
4. Override configuration values
"""

import os
import tempfile
import yaml
from pathlib import Path
from omniq import OmniQ

def simple_task(x, y):
    """Simple task function."""
    return x + y

def create_yaml_config_file(config_path):
    """Create a sample YAML configuration file."""
    config = {
        "project_name": "yaml_config_example",
        "task_queue": {
            "type": "sqlite",
            "config": {
                "base_dir": "./omniq_data",
                "queues": ["high", "medium", "low"]
            }
        },
        "result_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./omniq_data"
            }
        },
        "event_store": {
            "type": "sqlite",
            "config": {
                "base_dir": "./omniq_data"
            }
        },
        "worker": {
            "type": "async",
            "config": {
                "max_workers": 4
            }
        }
    }
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Created YAML configuration file at {config_path}")

def main_load_from_yaml():
    """Demonstrate loading configuration from YAML."""
    print("=== Loading Configuration from YAML ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a YAML configuration file
        config_path = Path(temp_dir) / "config.yaml"
        create_yaml_config_file(config_path)
        
        # Load configuration from YAML
        with OmniQ.from_config_file(str(config_path)) as oq:
            # Start a worker
            oq.start_worker()
            
            try:
                # Enqueue a task
                task_id = oq.enqueue(
                    func=simple_task,
                    func_args={"x": 5, "y": 10},
                    queue_name="high"
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = oq.get_result(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                oq.stop_worker()

def main_load_from_yaml_with_overrides():
    """Demonstrate loading configuration from YAML with overrides."""
    print("\n=== Loading Configuration from YAML with Overrides ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a YAML configuration file
        config_path = Path(temp_dir) / "config.yaml"
        create_yaml_config_file(config_path)
        
        # Load configuration from YAML with overrides
        with OmniQ.from_config_file(
            str(config_path),
            worker_type="thread_pool",
            worker_config={"max_workers": 2}
        ) as oq:
            # Start a worker
            oq.start_worker()
            
            try:
                # Enqueue a task
                task_id = oq.enqueue(
                    func=simple_task,
                    func_args={"x": 7, "y": 3},
                    queue_name="medium"
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = oq.get_result(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                oq.stop_worker()

def main_load_from_yaml_with_env_vars():
    """Demonstrate loading configuration from YAML with environment variables."""
    print("\n=== Loading Configuration from YAML with Environment Variables ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a YAML configuration file with environment variable placeholders
        config_path = Path(temp_dir) / "config.yaml"
        
        config = {
            "project_name": "${PROJECT_NAME:-env_config_example}",
            "task_queue": {
                "type": "sqlite",
                "config": {
                    "base_dir": "${BASE_DIR:-./omniq_data}",
                    "queues": ["high", "medium", "low"]
                }
            },
            "result_store": {
                "type": "sqlite",
                "config": {
                    "base_dir": "${BASE_DIR:-./omniq_data}"
                }
            },
            "event_store": {
                "type": "sqlite",
                "config": {
                    "base_dir": "${BASE_DIR:-./omniq_data}"
                }
            },
            "worker": {
                "type": "${WORKER_TYPE:-async}",
                "config": {
                    "max_workers": "${MAX_WORKERS:-4}"
                }
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        # Set environment variables
        os.environ["PROJECT_NAME"] = "env_example"
        os.environ["BASE_DIR"] = str(temp_dir)
        os.environ["WORKER_TYPE"] = "thread_pool"
        os.environ["MAX_WORKERS"] = "2"
        
        try:
            # Load configuration from YAML with environment variable substitution
            with OmniQ.from_config_file(str(config_path), env_vars=True) as oq:
                # Start a worker
                oq.start_worker()
                
                try:
                    # Enqueue a task
                    task_id = oq.enqueue(
                        func=simple_task,
                        func_args={"x": 8, "y": 2},
                        queue_name="low"
                    )
                    print(f"Enqueued task with ID: {task_id}")
                    
                    # Get the result
                    result = oq.get_result(task_id)
                    print(f"Result: {result}")
                    
                finally:
                    # Stop the worker
                    oq.stop_worker()
        
        finally:
            # Clean up environment variables
            for var in ["PROJECT_NAME", "BASE_DIR", "WORKER_TYPE", "MAX_WORKERS"]:
                if var in os.environ:
                    del os.environ[var]

def main_create_yaml_from_config():
    """Demonstrate creating a YAML file from a configuration object."""
    print("\n=== Creating YAML from Configuration Object ===")
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a configuration object
        from omniq.models.config import OmniQConfig, TaskQueueConfig, ResultStorageConfig, EventStorageConfig, WorkerConfig
        
        config = OmniQConfig(
            project_name="yaml_from_config_example",
            task_queue=TaskQueueConfig(
                type="sqlite",
                config={
                    "base_dir": str(temp_dir),
                    "queues": ["high", "medium", "low"]
                }
            ),
            result_store=ResultStorageConfig(
                type="sqlite",
                config={
                    "base_dir": str(temp_dir)
                }
            ),
            event_store=EventStorageConfig(
                type="sqlite",
                config={
                    "base_dir": str(temp_dir)
                }
            ),
            worker=WorkerConfig(
                type="async",
                config={
                    "max_workers": 4
                }
            )
        )
        
        # Save configuration to YAML
        config_path = Path(temp_dir) / "generated_config.yaml"
        config.to_yaml_file(config_path)
        
        print(f"Generated YAML configuration file at {config_path}")
        
        # Load and use the configuration
        with OmniQ.from_config_file(str(config_path)) as oq:
            # Start a worker
            oq.start_worker()
            
            try:
                # Enqueue a task
                task_id = oq.enqueue(
                    func=simple_task,
                    func_args={"x": 9, "y": 1},
                    queue_name="high"
                )
                print(f"Enqueued task with ID: {task_id}")
                
                # Get the result
                result = oq.get_result(task_id)
                print(f"Result: {result}")
                
            finally:
                # Stop the worker
                oq.stop_worker()

if __name__ == "__main__":
    # Run the basic YAML loading example
    main_load_from_yaml()
    
    # Run the YAML loading with overrides example
    main_load_from_yaml_with_overrides()
    
    # Run the YAML loading with environment variables example
    main_load_from_yaml_with_env_vars()
    
    # Run the create YAML from config example
    main_create_yaml_from_config()
```

## Implementation Notes

### Example Organization

The examples are organized to cover different aspects of OmniQ:

1. **Basic Usage**: Simple examples for getting started
2. **SQLite Backend**: Examples specific to the SQLite backend
3. **Scheduling**: Examples for task scheduling features
4. **Workers**: Examples for different worker types and configurations
5. **Advanced Usage**: Examples for advanced features
6. **Real-World Scenarios**: Examples for practical applications
7. **Configuration**: Examples for different configuration methods

### Example Quality

All examples follow these quality guidelines:

1. **Clear Purpose**: Each example has a clear, focused purpose
2. **Comprehensive Comments**: Detailed comments explain what's happening
3. **Error Handling**: Examples include proper error handling
4. **Realistic Scenarios**: Examples simulate real-world use cases
5. **Multiple Approaches**: Different ways to achieve the same goal are shown

### Example Documentation

Each example category includes a README file that:

1. **Explains the Purpose**: What the examples in the category demonstrate
2. **Lists Prerequisites**: What's needed to run the examples
3. **Provides Instructions**: How to run the examples
4. **Explains the Code**: What the code does and why

## Example Strategy

For Task 4, the following strategy is used:

1. **Progressive Complexity**: Examples start simple and increase in complexity
2. **Comprehensive Coverage**: Examples cover all major features
3. **Practical Focus**: Examples focus on real-world usage
4. **Multiple Approaches**: Different ways to use the same features are shown
5. **Clear Documentation**: Each example is well-documented

## Dependencies

Task 4 requires the following dependencies:

- Core: Same as Tasks 1, 2, and 3
- Examples: `aiosqlite`, `pyyaml` (for YAML configuration examples)

## Deliverables

1. Complete set of examples for all core features
2. Complete set of examples for SQLite backend features
3. Real-world scenario examples
4. Configuration examples
5. Documentation for all examples
6. Example data files where needed