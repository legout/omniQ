# OmniQ Documentation

Welcome to the official documentation for OmniQ, a modular Python task queue library designed for both local and distributed task processing. OmniQ adopts an "Async First, Sync Wrapped" architecture, ensuring high performance and flexibility while providing convenient synchronous wrappers for ease of use.

## Key Features

OmniQ is built with several core design principles in mind:

*   **Async First, Sync Wrapped**: Core library implemented asynchronously with synchronous wrappers using `anyio.from_thread.run()`.
*   **Separation of Concerns**: Task queue, result storage, and event logging are decoupled and independent components.
*   **Interface-Driven**: All components implement common interfaces, promoting extensibility and maintainability.
*   **Storage Independence**: Tasks, results, and events can utilize different backends independently, offering maximum flexibility.
*   **Multiple Storage Backends**: Supports various storage solutions including File (fsspec with cloud support), Memory, SQLite, PostgreSQL, Redis, and NATS.
*   **Multiple Worker Types**: Offers different execution engines such as Async, Thread Pool, Process Pool, and Gevent workers.
*   **Flexible Configuration**: Configurable via code, objects, dictionaries, YAML files, and environment variables.
*   **Cloud Storage Support**: Seamless integration with S3, Azure, and GCP through `fsspec`.
*   **Task Lifecycle Management**: Comprehensive features for task management including TTL (Time-To-Live), dependencies, and scheduling with pause/resume capabilities.
*   **Intelligent Serialization**: A dual serialization strategy using `msgspec` for compatible types and `dill` for complex Python objects.
*   **Multiple Named Queues**: Supports priority ordering across all backends.
*   **Event-Driven Architecture**: Non-blocking event logging for tracking task lifecycle events.

## Getting Started

To begin using OmniQ, refer to the [Getting Started](getting_started.md) guide for installation and basic usage instructions.

## API Reference

For detailed information on OmniQ's modules and classes, consult the [API Documentation](api/backends.md).