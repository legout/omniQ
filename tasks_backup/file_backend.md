# OmniQ File Backend: Think Mode Prompt

Analyze the following requirements and implementation notes to generate a detailed plan for implementing the File backend for OmniQ:

## Relevant Architecture

- The storage layer supports pluggable backends for task queues, result storage, and event storage.
- All components implement both async (core) and sync (wrapper) interfaces.
- Multiple named queues are supported via directory structure.
- The backend must support both context managers (sync and async).
- Task events are stored as JSON files.

## Implementation Details

- Use `fsspec` for file storage abstraction.
- Support the following storage locations:
  - Memory: `fsspec.MemoryFileSystem`
  - Local: `fsspec.LocalFileSystem` with `DirFileSystem` when possible
  - S3: `s3fs` (optional)
  - Azure: `adlfs` (optional)
  - GCP: `gcsfs` (optional)
- Use `base_dir` as the prefix for all file operations.
- Implement file storage for tasks, results, and events.
- Store task events as JSON files when using File Storage Backend for events.
- Support multiple named queues using directory structure.
- Implement TTL enforcement and cleanup for tasks.
- Support bulk operations and efficient file access.

## Prompt

**Generate a detailed implementation plan for the File backend, specifying:**
- The directory structure for supporting multiple named queues and storage types.
- The required async and sync interfaces and their methods.
- How to handle task TTL, locking, and schedule state using files.
- Strategies for efficient bulk operations and file management.
- How to store and query events as JSON files.
- How to support cloud storage backends via fsspec.
- Any edge cases or failure scenarios to consider.