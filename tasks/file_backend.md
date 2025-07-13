# OmniQ File Backend Implementation Task

## Project Description

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods. OmniQ enables developers to easily implement task queuing, scheduling, and distributed processing in their applications with both synchronous and asynchronous interfaces.

---

## Core Design Principles

- **Async First, Sync Wrapped:** All core functionality must be implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API.
- **Separation of Concerns:** Task queue, result storage, and event logging are decoupled and independent.
- **Interface-Driven:** All components implement common interfaces.
- **Storage Abstraction:** Use `fsspec` for file and memory storage with extended capabilities.
- **Cloud Storage Support:** Support for S3, Azure, and GCP via `fsspec` and its plugins.

---

## Module Architecture Focus

### `omniq.storage.file`

Implement the following classes:
- **AsyncFileQueue**: Core async implementation using `fsspec` with `DirFileSystem` (supports memory, local, S3, Azure, GCP).
- **FileQueue**: Synchronous wrapper around `AsyncFileQueue`.
- **AsyncFileResultStorage**: Async result storage using `fsspec`.
- **FileResultStorage**: Sync wrapper for result storage.
- **AsyncFileEventStorage**: Async event storage using `fsspec`, storing events as JSON files.
- **FileEventStorage**: Sync wrapper for event storage.

### `omniq.backend.file`

- Integrates the above storage classes into a cohesive backend.
- Exposes configuration and initialization for file-based task queue, result storage, and event storage.
- Ensures proper handling of `base_dir` and `storage_options` for all storage classes.

---

## Development Guidelines

### Async First, Sync Wrapped Implementation Guidelines

- Implement all core functionality using async/await.
- Create synchronous wrappers using `anyio.from_thread.run()` or event loops.
- Use `Async` prefix for core async classes, no prefix for sync wrappers.
- Implement both `__aenter__`/`__aexit__` and `__enter__`/`__exit__` context managers.
- Preserve exception context across sync/async boundaries.
- Ensure proper cleanup in both sync and async contexts.

**Example Pattern:**
```python
class AsyncFileQueue:
    async def enqueue(self, task):
        ...
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...

class FileQueue:
    def __init__(self, *args, **kwargs):
        self._async_queue = AsyncFileQueue(*args, **kwargs)
    def enqueue(self, task):
        return anyio.from_thread.run(self._async_queue.enqueue, task)
    def __enter__(self): ...
    def __exit__(self, exc_type, exc_val, exc_tb): ...
```

### Storage Implementation

- Implement multiple queues using directory structure for file-based queues.
- Use `fsspec` for file and memory storage with `DirFileSystem` when possible.
- Support optional cloud storage through `s3fs`, `gcsfs`, and `adlfs`.
- Implement both sync and async context managers.
- Use `base_dir` parameter in initialization as the prefix for all file operations.
- Support `storage_options` for cloud authentication/configuration.

### File Storage Implementation

- Support the following storage locations:
  - **Memory**: Using `fsspec.MemoryFileSystem`
  - **Local**: Using `fsspec.LocalFileSystem` with `DirFileSystem`
  - **S3**: Using `s3fs`
  - **Azure**: Using `adlfs`
  - **GCP**: Using `gcsfs`
- Leverage `fsspec` abstraction for all file operations.
- Store task events as JSON files when using File Storage Backend for events.

### Logging and Event Management

- Separate library logging from task events.
- Library logging is for debugging/monitoring the library itself.
- Task events are tracked by storing event data as JSON files in the event storage directory.
- Event storage is only enabled when explicitly configured.

---

## Scope

Fully implement the File backend, including:
- Task queue (AsyncFileQueue, FileQueue)
- Result storage (AsyncFileResultStorage, FileResultStorage)
- Event storage (AsyncFileEventStorage, FileEventStorage)

**Requirements:**
- Use `fsspec` to support local filesystem, in-memory, S3, Azure Data Lake, and Google Cloud Storage.
- Implement both asynchronous and synchronous interfaces for all operations.
- Ensure proper handling of `base_dir` and `storage_options` for all storage classes.
- Store events as JSON files.

---

## Dependencies

- `fsspec`
- `s3fs`
- `adlfs`
- `gcsfs`

---

## Completion

Signal completion of this task by using the `attempt_completion` tool with a summary of the created prompt.