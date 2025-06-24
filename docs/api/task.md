# Task API Documentation

The `Task` class in OmniQ represents a unit of work to be executed within the task queue system. It encapsulates the function to be run, its arguments, dependencies, callbacks, and various configuration options like timeouts and TTL (time-to-live). Tasks can be executed synchronously or asynchronously, making them versatile for different application needs.

## Class Definition

**Class**: `omniq.models.task.Task`

### Constructor Parameters

- **func** (`callable`): The function or callable to be executed as the task. This can be any Python callable, including regular functions, async functions, or lambda expressions.
- **id** (`str`, optional): A unique identifier for the task. If not provided, a UUID will be generated automatically.
- **args** (`tuple`, optional): Positional arguments to pass to the function when executed. Defaults to an empty tuple.
- **kwargs** (`dict`, optional): Keyword arguments to pass to the function when executed. Defaults to an empty dictionary.
- **dependencies** (`list`, optional): A list of task IDs that must be completed before this task can start. Defaults to an empty list.
- **callbacks** (`list`, optional): A list of callables to be executed after the task completes, regardless of success or failure. Defaults to an empty list.
- **timeout** (`float`, optional): The maximum time (in seconds) the task is allowed to run before being terminated. Defaults to `None`, meaning no timeout.
- **ttl** (`float`, optional): Time-to-live (in seconds) for the task, after which it may be cleaned up if not executed. Defaults to `None`, meaning no TTL.
- **status** (`str`, optional): The current status of the task (e.g., "pending", "running", "completed"). Defaults to "pending".
- **created_at** (`datetime`, optional): The timestamp when the task was created. Defaults to the current time if not provided.

### Key Attributes

- **func**: The callable to be executed.
- **id**: Unique identifier for the task.
- **args**: Positional arguments for the callable.
- **kwargs**: Keyword arguments for the callable.
- **dependencies**: List of task IDs that must complete before this task starts.
- **callbacks**: List of callables to execute after task completion.
- **timeout**: Time limit for task execution in seconds.
- **ttl**: Time-to-live for the task in seconds.
- **status**: Current state of the task.
- **created_at**: Timestamp of task creation.

### Methods

- **execute()**: Synchronously executes the task's function with the provided arguments and returns the result. If the task is an async function, it will raise a `RuntimeError` as async tasks should use `execute_async()`.
  - **Returns**: The result of the function execution.
  - **Raises**: Any exceptions raised by the function, or `TimeoutError` if the task exceeds its timeout.

- **execute_async()**: Asynchronously executes the task's function with the provided arguments and returns the result. This method is suitable for both sync and async functions, as it handles the event loop for async functions.
  - **Returns**: The result of the function execution.
  - **Raises**: Any exceptions raised by the function, or `TimeoutError` if the task exceeds its timeout.

- **add_callback(callback)**: Adds a callback function to be executed after the task completes.
  - **Parameters**:
    - **callback** (`callable`): The callback function to add.
  - **Returns**: None

- **add_dependency(task_id)**: Adds a dependency to the task, which must be completed before this task can start.
  - **Parameters**:
    - **task_id** (`str`): The ID of the task to depend on.
  - **Returns**: None

## Usage Examples

### Creating a Simple Task

```python
from omniq.models.task import Task

# Define a simple function to double a number
def double(x):
    return x * 2

# Create a task to execute the function with argument 5
task = Task(func=double, id="double-task", args=(5,))

# Execute the task synchronously
result = task.execute()
print(f"Result: {result}")  # Output: Result: 10
```

### Creating an Async Task

```python
from omniq.models.task import Task
import asyncio

# Define an async function to simulate an API call
async def fetch_data(url):
    # Simulate network delay
    await asyncio.sleep(1)
    return {"data": f"Response from {url}"}

# Create a task to execute the async function
task = Task(func=fetch_data, id="fetch-task", args=("https://api.example.com",))

# Execute the task asynchronously
result = asyncio.run(task.execute_async())
print(f"Result: {result}")  # Output: Result: {'data': 'Response from https://api.example.com'}
```

### Task with Dependencies and Callbacks

```python
from omniq.models.task import Task

# Define callback function
def on_complete(result):
    print(f"Task completed with result: {result}")

# Create tasks with dependencies and callbacks
task1 = Task(func=lambda x: x + 1, id="task-1", args=(10,))
task2 = Task(func=lambda x: x * 2, id="task-2", args=(task1.execute(),))
task2.add_dependency("task-1")
task2.add_callback(on_complete)

# Execute tasks (in a real scenario, a task queue would handle dependencies)
result1 = task1.execute()
print(f"Task 1 Result: {result1}")  # Output: Task 1 Result: 11
result2 = task2.execute()
print(f"Task 2 Result: {result2}")  # Output: Task 2 Result: 22
# Callback output: Task completed with result: 22
```

### Task with Timeout

```python
from omniq.models.task import Task
import time

# Define a long-running function
def long_running_task():
    time.sleep(5)
    return "Done"

# Create a task with a short timeout
task = Task(func=long_running_task, id="long-task", timeout=2.0)

# Execute the task (will raise TimeoutError)
try:
    result = task.execute()
except TimeoutError as e:
    print(f"Task timed out: {e}")  # Output: Task timed out: Task 'long-task' timed out after 2.0 seconds
```

## Notes

- The `Task` class is designed to be serializable for storage and transmission across different storage backends. Ensure that the `func`, `args`, and `kwargs` provided are serializable if the task needs to be stored or transmitted.
- When using async functions, always use `execute_async()` within an event loop context (e.g., via `asyncio.run()` or within an async framework like FastAPI).
- Dependencies and callbacks are managed by the task queue system, so in a real application, you would enqueue tasks with dependencies to a `TaskQueue` which handles the execution order.

This documentation provides a comprehensive overview of the `Task` class in OmniQ. For more information on integrating tasks with a task queue, refer to the [TaskQueue documentation](./task_queue.md).
