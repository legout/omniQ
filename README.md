# OmniQ - Modular Python Task Queue Library

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It supports scheduling, task dependencies, callbacks, event logging, and includes a dashboard for monitoring and management.

## Features

- **Dual Interface**: Provides both synchronous and asynchronous APIs for flexibility in usage.
- **Separation of Concerns**: Decouples task storage, result storage, and event logging for independent configuration.
- **Storage Abstraction**: Supports multiple storage backends including file, memory, SQLite, PostgreSQL, Redis, and NATS using `obstore` for enhanced capabilities.
- **Worker Flexibility**: Offers various worker types (async, thread, process, gevent) to handle different workloads.
- **Serialization Strategy**: Uses intelligent serialization with `msgspec` for performance and `dill` for complex objects.
- **Task Lifecycle Management**: Implements TTL for tasks and automatic cleanup of expired tasks.
- **Flexible Scheduling**: Allows pausing and resuming of scheduled tasks.
- **Comprehensive Dashboard**: Web interface for real-time task monitoring, schedule management, and metrics visualization.

## Architecture Overview

OmniQ is built with a modular architecture to ensure flexibility and scalability:

- **TaskQueue (Orchestrator)**: Central component managing task lifecycle.
- **Interface Layer**: Sync and async APIs for interaction.
- **Task Management Layer**: Handles task data models, scheduling, and dependency resolution.
- **Storage Layer**: Independent storage for tasks, results, and events with multiple backend options.
- **Execution Layer**: Manages worker pools and task execution with lifecycle callbacks.
- **Dashboard Layer**: Web interface for monitoring and control.

## Installation

(Instructions will be added once the library is ready for distribution.)

## Usage

(Examples will be provided as the library development progresses.)

## Development

OmniQ is under active development. The project structure and dependencies are managed with `uv`. To contribute or explore the codebase:

```bash
# Clone the repository (if applicable)
git clone <repository-url>
cd omniQ

# Initialize the project environment
uv init

# Add dependencies (already set in pyproject.toml)
uv add obstore msgspec dill

# Add development dependencies
uv add --dev pytest ruff mypy
```

## License

This project is licensed under the MIT License - see the LICENSE file for details (to be added).

## Contact

For inquiries or contributions, please contact the project maintainers (details to be added).
