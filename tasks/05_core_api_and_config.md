# Task 5: Core API (`OmniQ`) and Configuration System

## Objective
To implement the main entry point for the library, the `OmniQ` class, which orchestrates the different components. Additionally, a flexible configuration system will be developed to allow users to easily set up and customize the library's behavior.

## Requirements

### 1. Core `OmniQ` Class (`src/omniq/core.py`)
- Create a `core.py` file in the `src/omniq/` directory.
- Implement the `AsyncOmniQ` class as the main asynchronous entry point.
- `AsyncOmniQ` will:
    - Initialize and manage the task queue, result storage, event storage, and worker instances.
    - Provide high-level API methods like `enqueue()`, `get_result()`, and `schedule()`.
    - Implement `__aenter__` and `__aexit__` for use as an async context manager.
- Implement the `OmniQ` class as a synchronous wrapper around `AsyncOmniQ`, following the "Async First, Sync Wrapped" pattern. It will provide the same API but in a blocking manner.
- The `OmniQ` classes should be configurable to use different backend implementations for each component.

### 2. Configuration System (`src/omniq/config/`)
- Create the necessary files in the `src/omniq/config/` directory.

#### `src/omniq/config/settings.py`
- Define default settings for the library as Python constants (e.g., `DEFAULT_WORKER = 'async'`). These constants should NOT have an "OMNIQ_" prefix.

#### `src/omniq/config/env.py`
- Read environment variables to override the default settings.
- Environment variables should have an "OMNIQ_" prefix (e.g., `OMNIQ_DEFAULT_WORKER`).
- This file will provide configuration values that can be imported by other parts of the library.

#### `src/omniq/config/loader.py`
- Implement functions to load configuration from different sources:
    - `from_dict()`: Load configuration from a Python dictionary.
    - `from_yaml()`: Load configuration from a YAML file.
    - `from_object()`: Load configuration from a Python object.
- This loader will be used by the `OmniQ` class to allow for flexible setup.

#### `src/omniq/models/config.py`
- In the `src/omniq/models` directory, create a `config.py` file.
- Define `msgspec.Struct` based configuration objects for each component (e.g., `SQLiteQueueConfig`, `FileResultStorageConfig`).
- These objects will provide type validation for configurations.

## Completion Criteria
- `src/omniq/core.py` is created with the `AsyncOmniQ` and `OmniQ` classes implemented.
- The `OmniQ` classes can successfully orchestrate the queue, storage, and worker components.
- The configuration files (`settings.py`, `env.py`, `loader.py`) are created in `src/omniq/config/`.
- The configuration system can load settings from environment variables, dictionaries, objects, and YAML files.
- Configuration models are defined in `src/omniq/models/config.py` using `msgspec.Struct`.
- The library can be fully configured and instantiated through the `OmniQ` class.