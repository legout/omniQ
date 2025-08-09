# Task 9: File and Memory Storage Backends

## Objective
To implement the File and Memory storage backends for the OmniQ library, including task queues, result storage, and event storage (for FileBackend).

## Requirements

### 1. File Backend Implementation (`src/omniq/queue/file.py`, `src/omniq/results/file.py`, `src/omniq/events/file.py`)
- Implement `AsyncFileQueue` and `FileQueue` for task queues using `fsspec` with `DirFileSystem` for local storage and supporting cloud storage (S3, Azure, GCP) via `base_dir` and `storage_options`.
- Implement `AsyncFileResultStorage` and `FileResultStorage` for result storage using `fsspec` and supporting cloud storage.
- Implement `AsyncFileEventStorage` and `FileEventStorage` for event storage, storing events as JSON files using `fsspec` and supporting cloud storage.
- Ensure all implementations follow the "Async First, Sync Wrapped" design principle.
- Implement task locking mechanism for FileQueue.

### 2. Memory Backend Implementation (`src/omniq/queue/memory.py`, `src/omniq/results/memory.py`)
- Implement `AsyncMemoryQueue` and `MemoryQueue` for in-memory task queues using `fsspec.MemoryFileSystem`.
- Implement `AsyncMemoryResultStorage` and `MemoryResultStorage` for in-memory result storage.
- Ensure all implementations follow the "Async First, Sync Wrapped" design principle.
- Implement task locking mechanism for MemoryQueue.

### 3. Backend Integration (`src/omniq/backend/file.py`, `src/omniq/backend/memory.py`)
- In `src/omniq/backend/file.py`, implement `FileBackend` which creates instances of `FileQueue`, `FileResultStorage`, and `FileEventStorage`.
- In `src/omniq/backend/memory.py`, implement `MemoryBackend` which creates instances of `MemoryQueue` and `MemoryResultStorage`.

## Completion Criteria
- `src/omniq/queue/file.py` and `src/omniq/queue/memory.py` are created with `AsyncFileQueue`/`FileQueue` and `AsyncMemoryQueue`/`MemoryQueue` respectively.
- `src/omniq/results/file.py` and `src/omniq/results/memory.py` are created with `AsyncFileResultStorage`/`FileResultStorage` and `AsyncMemoryResultStorage`/`MemoryResultStorage` respectively.
- `src/omniq/events/file.py` is created with `AsyncFileEventStorage`/`FileEventStorage`.
- `src/omniq/backend/file.py` and `src/omniq/backend/memory.py` are created with `FileBackend` and `MemoryBackend` respectively.
- All implementations correctly use `fsspec` for their respective storage types and support the "Async First, Sync Wrapped" pattern.
- Task locking mechanisms are implemented for both FileQueue and MemoryQueue.