# Basic Usage Examples

This directory contains basic usage examples for the OmniQ library, demonstrating both synchronous and asynchronous interfaces.

## Files

- **`async_usage.py`**: Demonstrates basic usage with `AsyncOmniQ` for asynchronous task processing
- **`sync_usage.py`**: Demonstrates basic usage with `OmniQ` for synchronous task processing  
- **`basic_usage.ipynb`**: Jupyter notebook containing both async and sync examples with detailed explanations

## Overview

These examples show how to:

1. Create an OmniQ instance with different storage backends
2. Define and enqueue tasks
3. Start and manage workers
4. Retrieve task results
5. Schedule recurring tasks
6. Use context managers for proper resource management

The examples use a combination of:
- **File-based task queue** for task storage
- **SQLite result storage** for storing task results
- **PostgreSQL event storage** for task lifecycle logging

Both synchronous and asynchronous versions demonstrate the same functionality, allowing you to choose the interface that best fits your application's architecture.