# OmniQ API Documentation

Welcome to the API documentation for OmniQ, a modular Python task queue library designed for both local and distributed task processing. OmniQ supports synchronous and asynchronous interfaces, offering flexibility for various use cases with features like task scheduling, dependencies, callbacks, and real-time monitoring through a web dashboard.

## Overview

OmniQ is built with a focus on modularity and extensibility, allowing developers to customize components such as storage backends, worker types, and serialization strategies. This documentation provides detailed information on the core components, their APIs, and how to integrate them into your applications.

## Core Components

### Task
Represents a unit of work to be executed. Tasks can be synchronous or asynchronous and support arguments, keyword arguments, dependencies, callbacks, timeouts, and TTL (time-to-live).

- **Class**: `omniq.models.task.Task`
- **Key Attributes**:
  - `func`: The callable to execute.
  - `args` and `kwargs`: Arguments and keyword arguments for the callable.
  - `id`: Unique identifier for the task.
  - `dependencies`: List of task IDs that must complete before this task can start.
  - `callbacks`: List of callables to execute after task completion.
  - `timeout` and `ttl`: Time constraints for task execution and lifetime.
  - `status`: Current state of the task (e.g., "pending", "running", "completed").

### TaskQueue
Manages the queuing and execution of tasks. OmniQ provides both synchronous and asynchronous implementations.

- **Sync Class**: `omniq.queue.sync_task_queue.SyncTaskQueue`
- **Async Class**: `omniq.queue.async_task_queue.AsyncTaskQueue`
- **Key Methods**:
  - `enqueue(task)`: Add a task to the queue for execution.
  - `dequeue()`: Retrieve a task from the queue for processing.
  - `get_result(task_id)`: Retrieve the result of a completed task.

### Scheduler
Handles scheduling of tasks based on intervals, cron expressions, or specific timestamps.

- **Class**: `omniq.queue.scheduler.Scheduler`
- **Key Methods**:
  - `add_schedule(schedule)`: Add a new schedule for recurring or one-time task execution.
  - `remove_schedule(schedule_id)`: Remove a schedule by its ID.
  - `pause_schedule(schedule_id)` and `resume_schedule(schedule_id)`: Control schedule execution state.
  - `is_due(schedule_id)`: Check if a schedule is due for execution.

### Workers
Execute tasks from the queue. OmniQ supports multiple worker types for different execution models.

- **Base Class**: `omniq.workers.base.BaseWorker`
- **Types**:
  - `AsyncWorker`: For asynchronous task execution.
  - `ThreadWorker`: For threaded execution.
  - `ProcessWorker`: For process-based execution.
  - `GeventWorker`: For gevent-based execution.
- **Key Methods**:
  - `start()`: Begin processing tasks from the queue.
  - `stop()`: Halt processing of tasks.

### Storage
Abstracts storage for tasks, results, and events. OmniQ supports multiple backends through the `obstore` library.

- **Base Class**: `omniq.storage.base.BaseStorage`
- **Implementations**:
  - `SQLiteStorage`: Local storage using SQLite.
  - `PostgresStorage`: Distributed storage using PostgreSQL.
- **Key Methods**:
  - `save_task(task)`: Store a task in the backend.
  - `get_task(task_id)`: Retrieve a task by ID.
  - `save_result(result)`: Store the result of a task.
  - `get_result(task_id)`: Retrieve the result of a task.

### Serialization
Handles serialization and deserialization of tasks and results for storage and transmission.

- **Manager Class**: `omniq.serialization.manager.SerializationManager`
- **Strategies**:
  - `MsgspecSerializer`: High-performance serialization using `msgspec`.
  - `DillSerializer`: Fallback for complex objects using `dill`.
- **Key Methods**:
  - `serialize(obj)`: Convert an object to a serialized format.
  - `deserialize(data)`: Convert serialized data back to an object.

### Events
Provides event logging for task lifecycle monitoring.

- **Logger Class**: `omniq.events.logger.EventLogger`
- **Key Methods**:
  - `log_event(event)`: Log a task lifecycle event.
  - `get_events(task_id)`: Retrieve events for a specific task.

## Getting Started

To quickly integrate OmniQ into your project, refer to the following basic usage example:

```python
from omniq.queue.async_task_queue import AsyncTaskQueue
from omniq.models.task import Task
from omniq.workers.async_worker import AsyncWorker
import asyncio

async def main():
    # Initialize the task queue
    queue = AsyncTaskQueue()
    
    # Create a simple task
    task = Task(func=lambda x: x * 2, args=(5,), id="example-task")
    
    # Enqueue the task
    await queue.enqueue(task)
    
    # Start a worker to process tasks
    worker = AsyncWorker(queue)
    worker.start()
    
    # Wait for the task to complete and get the result
    result = await queue.get_result("example-task")
    print(f"Task result: {result}")  # Output: Task result
