# Task 11: Advanced Scheduling and Dependencies

## Objective
To implement advanced task scheduling capabilities, including a dedicated scheduler component, and task dependency management.

## Requirements

### 1. Schedule Model (`src/omniq/models/schedule.py`)
- Define a `Schedule` struct using `msgspec.Struct` that includes fields for:
    - `id` (UUID)
    - `func_name` (string)
    - `args` (tuple)
    - `kwargs` (dict)
    - `interval` (timedelta, optional)
    - `cron` (string, optional)
    - `start_at` (datetime)
    - `end_at` (datetime, optional)
    - `last_run_at` (datetime, optional)
    - `next_run_at` (datetime, optional)
    - `is_paused` (boolean, default False)
    - `queue_name` (string)
- Ensure the model supports pause/resume capability.

### 2. AsyncScheduler and Scheduler (`src/omniq/queue/scheduler.py`)
- Create `src/omniq/queue/scheduler.py`.
- Implement `AsyncScheduler` and `Scheduler` (sync wrapper) to manage recurring tasks.
- The scheduler should:
    - Periodically check for schedules that are due to run.
    - Enqueue tasks based on `interval` or `cron` expressions.
    - Update `last_run_at` and `next_run_at` in the `Schedule` model.
    - Respect `start_at`, `end_at`, and `is_paused` states.
    - Interact with the task queue to enqueue tasks.

### 3. Task Dependencies and Workflow Management (`src/omniq/models/task.py`, `src/omniq/queue/dependency.py`)
- Modify the `Task` model in `src/omniq/models/task.py` to include a field for `dependencies: List[UUID]`.
- Create `src/omniq/queue/dependency.py`.
- Implement a `DependencyResolver` that:
    - Manages the dependency graph of tasks.
    - Determines when dependent tasks are ready to be enqueued.
    - Integrates with the task queue to only enqueue tasks whose dependencies are met.

## Completion Criteria
- `src/omniq/models/schedule.py` is created with the `Schedule` model.
- `src/omniq/queue/scheduler.py` is created with `AsyncScheduler` and `Scheduler`.
- The `schedule()` method in `src/omniq/core.py` is updated to utilize the new scheduler.
- The `Task` model in `src/omniq/models/task.py` is updated to include dependencies.
- `src/omniq/queue/dependency.py` is created with `DependencyResolver` to manage task dependencies.