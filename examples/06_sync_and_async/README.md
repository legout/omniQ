# Handling Both Sync and Async Tasks

This directory demonstrates how OmniQ workers can seamlessly handle both synchronous and asynchronous tasks, showcasing the library's flexibility in mixed workload scenarios.

## Files

- **`sync_and_async.py`**: Demonstrates how to enqueue and execute both sync and async tasks using different worker types
- **`sync_and_async.ipynb`**: Interactive Jupyter notebook showing the execution of mixed sync/async tasks with different worker configurations

## Overview

This example shows how to:

1. Define both synchronous and asynchronous task functions
2. Use different worker types (AsyncWorker, ThreadWorker) to handle mixed workloads
3. Enqueue both sync and async tasks to the same queue
4. Retrieve results from both task types
5. Understand how different workers handle sync vs async tasks internally

## Key Concepts

### Worker Behavior with Mixed Tasks

- **AsyncWorker**: 
  - Executes async tasks natively using `await`
  - Runs sync tasks in a thread pool to avoid blocking the event loop
  
- **ThreadWorker**: 
  - Executes sync tasks natively in thread pool
  - Runs async tasks by creating new event loops in threads

### Task Execution Strategy

OmniQ automatically detects whether a task function is synchronous or asynchronous and handles execution appropriately:

- **Sync tasks**: Regular Python functions that return values directly
- **Async tasks**: Coroutine functions defined with `async def` that can use `await`

## Example Components

The examples use:
- **File-based task queue** for task storage
- **SQLite result storage** for storing task results  
- **Mixed sync/async task functions** to demonstrate flexibility
- **Different worker types** to show execution strategies

This demonstrates OmniQ's ability to handle heterogeneous workloads where some tasks are I/O-bound (better suited for async) and others are CPU-bound (better suited for sync execution).