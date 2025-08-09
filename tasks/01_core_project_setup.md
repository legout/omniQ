# Task 1: Core Project Setup and Data Models

## Objective
Establish the foundational project structure and define the core data models for the OmniQ library. This task is the starting point for building the library and ensures that all subsequent components have a common set of data structures to work with.

## Requirements

### 1. Project Structure
- Create the necessary directories as defined in the `OmniQ_Project_Plan.md`.
- Specifically, create the following directory structure inside `src/omniq/`:
    - `models/`
    - `storage/`
    - `serialization/`
    - `queue/`
    - `workers/`
    - `events/`
    - `config/`
    - `backend/`
- Create `__init__.py` files in each of these new directories to make them Python packages.
- Also create a `py.typed` file in `src/omniq/` to support PEP 561.

### 2. Core Data Models (`src/omniq/models/`)
- Implement the initial data models in the `src/omniq/models/` directory.
- Use `msgspec.Struct` for all data models for performance and type validation.
- The models should be created in separate files as specified in the project plan.

#### `src/omniq/models/task.py`
- Define a `Task` struct.
- It should include fields for:
    - `id` (e.g., `UUID`)
    - `func_name` (string)
    - `args` (tuple)
    - `kwargs` (dict)
    - `created_at` (datetime)
    - `ttl` (timedelta, optional)

#### `src/omniq/models/result.py`
- Define a `TaskResult` struct.
- It should include fields for:
    - `task_id`
    - `status` (e.g., an `Enum` with values like `PENDING`, `SUCCESS`, `FAILURE`)
    - `result_data` (any)
    - `timestamp` (datetime)
    - `ttl` (timedelta, optional)

#### `src/omniq/models/event.py`
- Define a `TaskEvent` struct.
- It should include fields for:
    - `task_id`
    - `event_type` (e.g., an `Enum` with values like `ENQUEUED`, `STARTED`, `COMPLETED`, `FAILED`)
    - `timestamp` (datetime)
    - `worker_id` (string, optional)

## Completion Criteria
- The specified directory structure is created under `src/omniq/`.
- The core data model files (`task.py`, `result.py`, `event.py`) are created in `src/omniq/models/`.
- The data models (`Task`, `TaskResult`, `TaskEvent`) are implemented using `msgspec.Struct` with the specified fields.
- All new directories contain an `__init__.py` file.
- The `src/omniq/py.typed` file is created.