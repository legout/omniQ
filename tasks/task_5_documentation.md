# Task 5: Documentation for Implemented Core and SQLite Backend

## Overview

This task involves creating comprehensive documentation for OmniQ's core components and SQLite backend using Quarto. The documentation will include user guides, API references, examples, and contributing guidelines.

## Objectives

1. Set up a Quarto project for documentation
2. Create user guides for core features
3. Create API references for all components
4. Create examples and tutorials
5. Create contributing guidelines

## Detailed Implementation Plan

### 5.1 Quarto Project Setup

**Purpose**: Set up the Quarto project structure and configuration.

**Implementation Requirements**:
- Create a Quarto project using `quarto create project website`
- Configure `_quarto.yml` for navigation and output
- Set up the directory structure for documentation files
- Configure themes and styling

**Directory Structure**:
```
docs/
├── _quarto.yml                  # Quarto configuration
├── _freeze/                     # Freeze directory for computational documents
├── _extensions/                 # Quarto extensions
├── styles/                      # Custom CSS styles
│   └── custom.css               # Custom styling
├── images/                      # Images and diagrams
│   ├── architecture.png         # System architecture diagram
│   ├── data_flow.png            # Data flow diagram
│   └── logo.png                 # Project logo
├── index.qmd                    # Home page
├── installation.qmd             # Installation guide
├── quickstart.qmd               # Quick start guide
├── user_guide/                  # User guides
│   ├── index.qmd                # User guide overview
│   ├── getting_started.qmd      # Getting started guide
│   ├── core_concepts.qmd        # Core concepts
│   ├── task_queues.qmd          # Task queues guide
│   ├── scheduling.qmd           # Task scheduling guide
│   ├── workers.qmd              # Workers guide
│   ├── backends.qmd             # Backends guide
│   ├── configuration.qmd        # Configuration guide
│   └── advanced_features.qmd    # Advanced features guide
├── api/                         # API reference
│   ├── index.qmd                # API reference overview
│   ├── core.qmd                 # Core API
│   ├── models.qmd               # Models API
│   ├── backends.qmd             # Backends API
│   ├── storage.qmd              # Storage API
│   ├── workers.qmd              # Workers API
│   └── serialization.qmd        # Serialization API
├── examples/                    # Examples and tutorials
│   ├── index.qmd                # Examples overview
│   ├── basic_usage.qmd          # Basic usage examples
│   ├── sqlite_backend.qmd       # SQLite backend examples
│   ├── scheduling.qmd           # Scheduling examples
│   ├── workers.qmd              # Worker examples
│   ├── advanced.qmd             # Advanced examples
│   └── real_world.qmd           # Real-world examples
├── contributing.qmd             # Contributing guidelines
└── references.bib               # Bibliography references
```

### 5.2 Quarto Configuration (`docs/_quarto.yml`)

**Purpose**: Configure the Quarto project for navigation, output, and styling.

**Implementation Requirements**:
- Set up the site navigation
- Configure HTML output with the cosmo theme
- Enable search and table of contents
- Configure bibliography and cross-references

**Code Structure**:
```yaml
# docs/_quarto.yml
project:
  type: website
  output-dir: _site

website:
  title: "OmniQ Documentation"
  site-url: "https://omniq.readthedocs.io"
  description: "Documentation for OmniQ, a flexible task queue library for Python"
  
  navbar:
    background: primary
    search: true
    left:
      - text: "Home"
        href: index.qmd
      - text: "User Guide"
        menu: 
          - text: "Getting Started"
            href: user_guide/getting_started.qmd
          - text: "Core Concepts"
            href: user_guide/core_concepts.qmd
          - text: "Task Queues"
            href: user_guide/task_queues.qmd
          - text: "Scheduling"
            href: user_guide/scheduling.qmd
          - text: "Workers"
            href: user_guide/workers.qmd
          - text: "Backends"
            href: user_guide/backends.qmd
          - text: "Configuration"
            href: user_guide/configuration.qmd
          - text: "Advanced Features"
            href: user_guide/advanced_features.qmd
      - text: "API Reference"
        menu:
          - text: "Overview"
            href: api/index.qmd
          - text: "Core API"
            href: api/core.qmd
          - text: "Models"
            href: api/models.qmd
          - text: "Backends"
            href: api/backends.qmd
          - text: "Storage"
            href: api/storage.qmd
          - text: "Workers"
            href: api/workers.qmd
          - text: "Serialization"
            href: api/serialization.qmd
      - text: "Examples"
        menu:
          - text: "Overview"
            href: examples/index.qmd
          - text: "Basic Usage"
            href: examples/basic_usage.qmd
          - text: "SQLite Backend"
            href: examples/sqlite_backend.qmd
          - text: "Scheduling"
            href: examples/scheduling.qmd
          - text: "Workers"
            href: examples/workers.qmd
          - text: "Advanced"
            href: examples/advanced.qmd
          - text: "Real World"
            href: examples/real_world.qmd
    right:
      - icon: github
        href: "https://github.com/your-org/omniq"
      - icon: book
        href: "https://omniq.readthedocs.io"
  
  sidebar:
    style: "docked"
    search: true
    contents:
      - section: "User Guide"
        contents:
          - user_guide/getting_started.qmd
          - user_guide/core_concepts.qmd
          - user_guide/task_queues.qmd
          - user_guide/scheduling.qmd
          - user_guide/workers.qmd
          - user_guide/backends.qmd
          - user_guide/configuration.qmd
          - user_guide/advanced_features.qmd
      - section: "API Reference"
        contents:
          - api/index.qmd
          - api/core.qmd
          - api/models.qmd
          - api/backends.qmd
          - api/storage.qmd
          - api/workers.qmd
          - api/serialization.qmd
      - section: "Examples"
        contents:
          - examples/index.qmd
          - examples/basic_usage.qmd
          - examples/sqlite_backend.qmd
          - examples/scheduling.qmd
          - examples/workers.qmd
          - examples/advanced.qmd
          - examples/real_world.qmd
      - contributing.qmd

format:
  html:
    theme: cosmo
    css: styles/custom.css
    toc: true
    toc-depth: 4
    toc-location: left
    code-fold: false
    code-tools: true
    highlight-style: github
    include-in-header:
      - text: |
          <link rel="icon" href="images/logo.png" type="image/png">
    include-before-body:
      - text: |
          <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
          <script>mermaid.initialize({startOnLoad:true});</script>

execute:
  freeze: auto
  cache: true

bibliography: references.bib
```

### 5.3 Home Page (`docs/index.qmd`)

**Purpose**: Create the home page for the documentation.

**Implementation Requirements**:
- Introduce OmniQ and its purpose
- Highlight key features
- Provide links to getting started
- Include badges for GitHub, PyPI, etc.

**Code Structure**:
```markdown
---
title: OmniQ Documentation
---

::: {.hero}
# OmniQ

A flexible task queue library for Python

::: {.hero-buttons}
[Get Started](user_guide/getting_started.qmd){.btn .btn-primary .btn-lg}
[View on GitHub](https://github.com/your-org/omniq){.btn .btn-outline-primary .btn-lg}
:::
:::

OmniQ is a modular Python task queue library designed for both local and distributed task processing. It provides a flexible architecture that supports multiple storage backends, worker types, and configuration methods.

## Key Features

- **Multiple Storage Backends**: File, Memory, SQLite, PostgreSQL, Redis, NATS
- **Flexible Workers**: Async, Thread Pool, Process Pool, Gevent
- **Task Scheduling**: Cron and interval patterns with pause/resume
- **Task Dependencies**: Define and manage task workflows
- **Event Logging**: Track task lifecycle events
- **Result Storage**: Store and retrieve task results
- **Flexible Configuration**: Code, objects, dictionaries, YAML, environment variables
- **Multiple Queues**: Named queues with priority ordering
- **Cloud Storage**: Support for S3, Azure, GCP through fsspec
- **Task TTL**: Automatic cleanup of expired tasks

## Quick Example

```{python}
#| echo: true
#| eval: false
from omniq import OmniQ

# Define a simple task
def add_numbers(x, y):
    return x + y

# Create an OmniQ instance with SQLite backend
with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Start a worker
    oq.start_worker(worker_type="thread_pool", max_workers=2)
    
    try:
        # Enqueue a task
        task_id = oq.enqueue(
            func=add_numbers,
            func_args={"x": 5, "y": 10}
        )
        
        # Get the result
        result = oq.get_result(task_id)
        print(f"Result: {result}")  # Output: Result: 15
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Installation

```bash
pip install omniq
```

For SQLite backend support:

```bash
pip install omniq[sqlite]
```

## Getting Started

- [Installation Guide](installation.qmd)
- [Quick Start Guide](quickstart.qmd)
- [User Guide](user_guide/index.qmd)
- [API Reference](api/index.qmd)
- [Examples](examples/index.qmd)

## Contributing

We welcome contributions! Please see our [Contributing Guide](contributing.qmd) for details.

::: {.callout-note}
OmniQ is designed to be flexible and powerful, yet easy to use. Whether you need a simple local task queue or a complex distributed system, OmniQ can handle your needs.
:::
```

### 5.4 Installation Guide (`docs/installation.qmd`)

**Purpose**: Provide detailed installation instructions.

**Implementation Requirements**:
- Explain installation methods
- List dependencies and optional extras
- Provide troubleshooting tips
- Include instructions for different environments

**Code Structure**:
```markdown
---
title: Installation
---

# Installation

This guide covers how to install OmniQ and its dependencies.

## Prerequisites

OmniQ requires Python 3.8 or higher. You can check your Python version with:

```bash
python --version
```

## Basic Installation

Install OmniQ using pip:

```bash
pip install omniq
```

This installs the core library with minimal dependencies.

## Optional Extras

OmniQ provides several optional extras for additional functionality:

### SQLite Backend

For SQLite backend support:

```bash
pip install omniq[sqlite]
```

### PostgreSQL Backend

For PostgreSQL backend support:

```bash
pip install omniq[postgres]
```

### Redis Backend

For Redis backend support:

```bash
pip install omniq[redis]
```

### NATS Backend

For NATS backend support:

```bash
pip install omniq[nats]
```

### Cloud Storage

For cloud storage support (S3, Azure, GCP):

```bash
pip install omniq[cloud]
```

### All Extras

To install all optional extras:

```bash
pip install omniq[all]
```

### Development Installation

For development, install with development dependencies:

```bash
pip install omniq[dev]
```

This includes testing, linting, and documentation tools.

## Installation with uv

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. You can use it to install OmniQ:

```bash
uv pip install omniq
```

With extras:

```bash
uv pip install "omniq[sqlite,postgres]"
```

## Installation with pixi

[pixi](https://github.com/prefix-dev/pixi) is a package management tool for Python. You can use it to install OmniQ:

```bash
pixi add omniq
```

With extras:

```bash
pixi add "omniq[sqlite,postgres]"
```

## Installation from Source

To install OmniQ from source:

```bash
git clone https://github.com/your-org/omniq.git
cd omniq
pip install .
```

For development:

```bash
git clone https://github.com/your-org/omniq.git
cd omniq
pip install -e .
```

## Verification

To verify that OmniQ is installed correctly:

```python
import omniq
print(omniq.__version__)
```

You should see the version number of OmniQ.

## Troubleshooting

### Permission Errors

If you encounter permission errors during installation, consider using a virtual environment:

```bash
python -m venv omniq-env
source omniq-env/bin/activate  # On Windows: omniq-env\Scripts\activate
pip install omniq
```

### Dependency Conflicts

If you encounter dependency conflicts, try installing in a clean virtual environment:

```bash
python -m venv clean-env
source clean-env/bin/activate  # On Windows: clean-env\Scripts\activate
pip install omniq
```

### Missing Dependencies

If you encounter missing dependencies for a specific backend, make sure you've installed the appropriate extras:

```bash
pip install "omniq[sqlite]"  # For SQLite backend
pip install "omniq[postgres]"  # For PostgreSQL backend
pip install "omniq[redis]"  # For Redis backend
pip install "omniq[nats]"  # For NATS backend
pip install "omniq[cloud]"  # For cloud storage
```

### Windows-Specific Issues

On Windows, you may need to install Microsoft Visual C++ Build Tools for some dependencies:

1. Download and install [Microsoft Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Select "C++ build tools" during installation
3. Retry the OmniQ installation

### macOS-Specific Issues

On macOS, you may need to install Xcode Command Line Tools:

```bash
xcode-select --install
```

### Linux-Specific Issues

On Linux, you may need to install development headers for Python and SQLite:

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libsqlite3-dev

# CentOS/RHEL/Fedora
sudo yum install python3-devel sqlite-devel
```

## Next Steps

After installing OmniQ, check out the [Quick Start Guide](quickstart.qmd) to get started with your first task queue.
```

### 5.5 Quick Start Guide (`docs/quickstart.qmd`)

**Purpose**: Provide a quick introduction to using OmniQ.

**Implementation Requirements**:
- Show basic usage with minimal setup
- Include both sync and async examples
- Cover the most common use cases
- Provide clear explanations

**Code Structure**:
```markdown
---
title: Quick Start
---

# Quick Start Guide

This guide will help you get started with OmniQ quickly. We'll cover the basics of creating a task queue, enqueuing tasks, and retrieving results.

## Basic Setup

First, let's set up a simple task queue with OmniQ:

```{python}
#| echo: true
#| eval: false
from omniq import OmniQ

# Define a simple task function
def add_numbers(x, y):
    """Add two numbers and return the result."""
    return x + y

# Create an OmniQ instance with SQLite backend
with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Start a worker
    oq.start_worker(worker_type="thread_pool", max_workers=2)
    
    try:
        # Enqueue a task
        task_id = oq.enqueue(
            func=add_numbers,
            func_args={"x": 5, "y": 10}
        )
        print(f"Enqueued task with ID: {task_id}")
        
        # Get the result
        result = oq.get_result(task_id)
        print(f"Result: {result}")  # Output: Result: 15
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Asynchronous Usage

OmniQ also supports asynchronous operations:

```{python}
#| echo: true
#| eval: false
import asyncio
from omniq import OmniQ

# Define an async task function
async def async_add_numbers(x, y):
    """Asynchronously add two numbers and return the result."""
    await asyncio.sleep(0.1)  # Simulate async work
    return x + y

async def main():
    # Create an OmniQ instance with SQLite backend
    async with OmniQ(project_name="my_async_project", backend_type="sqlite") as oq:
        # Start a worker
        await oq.start_worker_async(worker_type="async", max_workers=2)
        
        try:
            # Enqueue a task
            task_id = await oq.enqueue_async(
                func=async_add_numbers,
                func_args={"x": 5, "y": 10}
            )
            print(f"Enqueued task with ID: {task_id}")
            
            # Get the result
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")  # Output: Result: 15
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

# Run the async example
asyncio.run(main())
```

## Multiple Tasks

You can enqueue and process multiple tasks:

```{python}
#| echo: true
#| eval: false
import time
from omniq import OmniQ

def process_data(data_id, processing_time=0.1):
    """Process some data with a simulated delay."""
    time.sleep(processing_time)
    return f"Processed data {data_id}"

with OmniQ(project_name="multi_task_project", backend_type="sqlite") as oq:
    # Start a worker with multiple threads
    oq.start_worker(worker_type="thread_pool", max_workers=4)
    
    try:
        # Enqueue multiple tasks
        task_ids = []
        for i in range(5):
            task_id = oq.enqueue(
                func=process_data,
                func_args={"data_id": i, "processing_time": 0.1}
            )
            task_ids.append(task_id)
        
        print(f"Enqueued {len(task_ids)} tasks")
        
        # Get all results
        results = []
        for task_id in task_ids:
            result = oq.get_result(task_id)
            results.append(result)
            print(f"Task {task_id}: {result}")
        
        print(f"Processed {len(results)} tasks")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Task Scheduling

OmniQ supports task scheduling:

```{python}
#| echo: true
#| eval: false
import datetime as dt
from omniq import OmniQ

def scheduled_task(name):
    """A task that can be scheduled."""
    return f"Hello, {name}!"

with OmniQ(project_name="scheduled_project", backend_type="sqlite") as oq:
    # Start a worker
    oq.start_worker(worker_type="thread_pool", max_workers=2)
    
    try:
        # Schedule a task to run in 10 seconds
        task_id = oq.enqueue(
            func=scheduled_task,
            func_args={"name": "World"},
            run_in=dt.timedelta(seconds=10)
        )
        print(f"Scheduled task with ID: {task_id}")
        
        # Schedule a recurring task every minute
        schedule_id = oq.schedule(
            func=scheduled_task,
            func_args={"name": "Recurring"},
            interval=dt.timedelta(minutes=1),
            max_runs=3
        )
        print(f"Scheduled recurring task with ID: {schedule_id}")
        
        # Wait for tasks to complete
        print("Waiting for tasks to complete...")
        time.sleep(120)  # Wait for all tasks to complete
        
        # Get the result of the scheduled task
        result = oq.get_result(task_id)
        print(f"Scheduled task result: {result}")
        
        # Get the results of the recurring task
        schedule_results = oq.get_result(schedule_id=schedule_id, kind="all")
        print(f"Recurring task results: {len(schedule_results)} runs")
        for i, result in enumerate(schedule_results):
            print(f"  Run {i+1}: {result}")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Multiple Queues

OmniQ supports multiple named queues with priority:

```{python}
#| echo: true
#| eval: false
from omniq import OmniQ

def process_task(task_name, priority):
    """Process a task with a given priority."""
    return f"Processed {task_name} with priority {priority}"

with OmniQ(
    project_name="multi_queue_project",
    backend_type="sqlite",
    queues=["high", "medium", "low"]
) as oq:
    # Start a worker
    oq.start_worker(worker_type="thread_pool", max_workers=2)
    
    try:
        # Enqueue tasks to different queues
        high_task_id = oq.enqueue(
            func=process_task,
            func_args={"task_name": "High Priority", "priority": "high"},
            queue_name="high"
        )
        
        medium_task_id = oq.enqueue(
            func=process_task,
            func_args={"task_name": "Medium Priority", "priority": "medium"},
            queue_name="medium"
        )
        
        low_task_id = oq.enqueue(
            func=process_task,
            func_args={"task_name": "Low Priority", "priority": "low"},
            queue_name="low"
        )
        
        print(f"Enqueued tasks to high, medium, and low priority queues")
        
        # Get all results
        high_result = oq.get_result(high_task_id)
        medium_result = oq.get_result(medium_task_id)
        low_result = oq.get_result(low_task_id)
        
        print(f"High priority task: {high_result}")
        print(f"Medium priority task: {medium_result}")
        print(f"Low priority task: {low_result}")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Configuration

OmniQ can be configured using YAML files:

```{python}
#| echo: true
#| eval: false
from omniq import OmniQ

# Create a configuration file
config_content = """
project_name: config_example
task_queue:
  type: sqlite
  config:
    queues:
      - high
      - medium
      - low
result_store:
  type: sqlite
event_store:
  type: sqlite
worker:
  type: thread_pool
  config:
    max_workers: 4
"""

# Write the configuration to a file
with open("config.yaml", "w") as f:
    f.write(config_content)

# Load configuration from the file
with OmniQ.from_config_file("config.yaml") as oq:
    # Start a worker
    oq.start_worker()
    
    try:
        # Enqueue a task
        task_id = oq.enqueue(
            func=lambda: "Hello from configured OmniQ!",
            queue_name="high"
        )
        
        # Get the result
        result = oq.get_result(task_id)
        print(f"Result: {result}")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

## Next Steps

This quick start guide covers the basics of OmniQ. For more detailed information, check out:

- [User Guide](user_guide/index.qmd) - Comprehensive guides for all features
- [API Reference](api/index.qmd) - Detailed API documentation
- [Examples](examples/index.qmd) - More examples and tutorials
```

### 5.6 User Guide - Core Concepts (`docs/user_guide/core_concepts.qmd`)

**Purpose**: Explain the core concepts of OmniQ.

**Implementation Requirements**:
- Explain the architecture and design principles
- Describe the main components and their relationships
- Include diagrams for visual understanding
- Provide context for more detailed guides

**Code Structure**:
```markdown
---
title: Core Concepts
---

# Core Concepts

This guide explains the core concepts and architecture of OmniQ. Understanding these concepts will help you make the most of OmniQ's features.

## Architecture Overview

OmniQ is designed with a modular architecture that separates concerns and provides flexibility. The main components are:

```{mermaid}
flowchart TD
    A[OmniQ] --> B[Task Queue]
    A --> C[Result Storage]
    A --> D[Event Storage]
    A --> E[Worker]
    
    B --> B1[File Queue]
    B --> B2[Memory Queue]
    B --> B3[SQLite Queue]
    B --> B4[PostgreSQL Queue]
    B --> B5[Redis Queue]
    B --> B6[NATS Queue]
    
    C --> C1[File Storage]
    C --> C2[Memory Storage]
    C --> C3[SQLite Storage]
    C --> C4[PostgreSQL Storage]
    C --> C5[Redis Storage]
    C --> C6[NATS Storage]
    
    D --> D1[SQLite Storage]
    D --> D2[PostgreSQL Storage]
    D --> D3[File Storage]
    
    E --> E1[Async Worker]
    E --> E2[Thread Pool Worker]
    E --> E3[Process Pool Worker]
    E --> E4[Gevent Pool Worker]
```

## Design Principles

OmniQ is built on the following design principles:

### Async First, Sync Wrapped

The core library is implemented asynchronously for maximum performance, with synchronous wrappers providing a convenient blocking API. This approach ensures that:

- Async operations are not hindered by sync compatibility
- Sync users get a simple, blocking interface
- Performance is optimized for async use cases

### Separation of Concerns

Task queue, result storage, and event logging are decoupled and independent. This allows:

- Different storage backends for each component
- Independent scaling of components
- Flexible configuration based on needs

### Interface-Driven

All components implement common interfaces, which enables:

- Easy swapping of implementations
- Consistent API across different backends
- Simplified testing and mocking

### Storage Abstraction

OmniQ uses `fsspec` for file and memory storage with extended capabilities, providing:

- Unified interface for different storage systems
- Support for cloud storage (S3, Azure, GCP)
- Easy addition of new storage backends

## Main Components

### OmniQ

The `OmniQ` class is the main entry point for the library. It provides:

- A high-level API for common operations
- Coordination between different components
- Simplified configuration and setup

### Task Queue

The task queue is responsible for:

- Storing tasks until they are ready to be processed
- Managing task priorities and dependencies
- Providing APIs for enqueuing and dequeuing tasks

OmniQ supports multiple task queue implementations:

- **File Queue**: Uses the filesystem for task storage
- **Memory Queue**: Stores tasks in memory (not persistent)
- **SQLite Queue**: Uses SQLite for task storage
- **PostgreSQL Queue**: Uses PostgreSQL for task storage
- **Redis Queue**: Uses Redis for task storage
- **NATS Queue**: Uses NATS for task storage

### Result Storage

Result storage is responsible for:

- Storing task results
- Providing APIs for retrieving results
- Managing result TTL and cleanup

OmniQ supports multiple result storage implementations:

- **File Storage**: Uses the filesystem for result storage
- **Memory Storage**: Stores results in memory (not persistent)
- **SQLite Storage**: Uses SQLite for result storage
- **PostgreSQL Storage**: Uses PostgreSQL for result storage
- **Redis Storage**: Uses Redis for result storage
- **NATS Storage**: Uses NATS for result storage

### Event Storage

Event storage is responsible for:

- Logging task lifecycle events
- Providing APIs for querying events
- Supporting event-based monitoring and debugging

OmniQ supports multiple event storage implementations:

- **SQLite Storage**: Uses SQLite for event storage
- **PostgreSQL Storage**: Uses PostgreSQL for event storage
- **File Storage**: Uses JSON files for event storage

### Worker

The worker is responsible for:

- Processing tasks from the queue
- Managing task execution
- Handling errors and retries

OmniQ supports multiple worker implementations:

- **Async Worker**: Uses asyncio for concurrent task processing
- **Thread Pool Worker**: Uses a thread pool for concurrent task processing
- **Process Pool Worker**: Uses a process pool for CPU-bound tasks
- **Gevent Pool Worker**: Uses gevent for coroutine-based concurrency

## Task Lifecycle

A task goes through several stages during its lifecycle:

```{mermaid}
flowchart LR
    A[Created] --> B[Enqueued]
    B --> C[Dequeued]
    C --> D[Executing]
    D --> E[Completed]
    D --> F[Failed]
    F --> G[Retrying]
    G --> D
    F --> H[Expired]
```

### Created

The task is created but not yet enqueued. At this stage, the task has:

- A unique ID
- A function to execute
- Arguments for the function
- Metadata (priority, TTL, etc.)

### Enqueued

The task is added to the queue. At this stage, the task has:

- A queue name
- An enqueue timestamp
- A status of "enqueued"

### Dequeued

The task is removed from the queue by a worker. At this stage, the task has:

- A dequeue timestamp
- A status of "dequeued"

### Executing

The task is being executed by a worker. At this stage, the task has:

- A start timestamp
- A status of "executing"
- A worker ID

### Completed

The task has completed successfully. At this stage, the task has:

- A completion timestamp
- A status of "completed"
- A result (if stored)

### Failed

The task has failed. At this stage, the task has:

- A failure timestamp
- A status of "failed"
- An error message and traceback

### Retrying

The task is being retried after a failure. At this stage, the task has:

- An incremented retry count
- A status of "retrying"
- A next retry time

### Expired

The task has expired (TTL reached). At this stage, the task has:

- An expiration timestamp
- A status of "expired"

## Data Flow

The following diagram shows the data flow in OmniQ:

```{mermaid}
sequenceDiagram
    participant Client
    participant OmniQ
    participant Queue as Task Queue
    participant Worker
    participant ResultStore as Result Storage
    participant EventStore as Event Storage
    
    Client->>OmniQ: enqueue(task)
    OmniQ->>Queue: enqueue(task)
    Queue-->>OmniQ: task_id
    OmniQ-->>Client: task_id
    
    Note over Queue: Task stored with queue name
    
    Worker->>Queue: dequeue(queues=["high", "medium", "low"])
    Queue-->>Worker: task
    
    Worker->>EventStore: log(EXECUTING)
    Worker->>Worker: execute(task)
    Worker->>ResultStore: store(result)
    Worker->>EventStore: log(COMPLETED)
    
    Client->>OmniQ: get_result(task_id)
    OmniQ->>ResultStore: get(task_id)
    ResultStore-->>OmniQ: result
    OmniQ-->>Client: result
```

## Configuration

OmniQ supports multiple configuration methods:

### Code Configuration

Configure OmniQ directly in code:

```python
from omniq import OmniQ

oq = OmniQ(
    project_name="my_project",
    backend_type="sqlite",
    queues=["high", "medium", "low"]
)
```

### Object Configuration

Configure using configuration objects:

```python
from omniq import OmniQ
from omniq.models.config import OmniQConfig, TaskQueueConfig

config = OmniQConfig(
    project_name="my_project",
    task_queue=TaskQueueConfig(
        type="sqlite",
        config={
            "queues": ["high", "medium", "low"]
        }
    )
)

oq = OmniQ.from_config(config)
```

### Dictionary Configuration

Configure using a dictionary:

```python
from omniq import OmniQ

config = {
    "project_name": "my_project",
    "task_queue": {
        "type": "sqlite",
        "config": {
            "queues": ["high", "medium", "low"]
        }
    }
}

oq = OmniQ.from_config_dict(config)
```

### YAML Configuration

Configure using a YAML file:

```python
from omniq import OmniQ

oq = OmniQ.from_config_file("config.yaml")
```

### Environment Variables

Configure using environment variables:

```python
from omniq import OmniQ

oq = OmniQ.from_env()
```

## Next Steps

Now that you understand the core concepts of OmniQ, you can explore more specific topics:

- [Task Queues](task_queues.qmd) - Learn about task queues in detail
- [Scheduling](scheduling.qmd) - Learn about task scheduling
- [Workers](workers.qmd) - Learn about different worker types
- [Backends](backends.qmd) - Learn about different storage backends
- [Configuration](configuration.qmd) - Learn about configuration options
- [Advanced Features](advanced_features.qmd) - Learn about advanced features
```

### 5.7 API Reference - Core (`docs/api/core.qmd`)

**Purpose**: Provide detailed API documentation for the core OmniQ components.

**Implementation Requirements**:
- Document all public classes and methods
- Include parameter descriptions and return types
- Provide code examples for each method
- Include cross-references to related components

**Code Structure**:
```markdown
---
title: Core API
---

# Core API Reference

This section provides detailed documentation for the core OmniQ components.

## OmniQ Class

The `OmniQ` class is the main entry point for the library. It provides a high-level API for common operations.

### Constructor

```python
OmniQ(
    project_name: str,
    backend_type: Optional[str] = None,
    backend: Optional[Backend] = None,
    task_queue: Optional[TaskQueue] = None,
    result_store: Optional[ResultStorage] = None,
    event_store: Optional[EventStorage] = None,
    queues: Optional[List[str]] = None,
    worker_type: Optional[str] = None,
    worker_config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None
```

Create a new OmniQ instance.

**Parameters:**

- `project_name` (str): The name of the project. Used for namespacing storage.
- `backend_type` (Optional[str]): The type of backend to use. One of "file", "memory", "sqlite", "postgres", "redis", "nats".
- `backend` (Optional[Backend]): A pre-configured backend instance.
- `task_queue` (Optional[TaskQueue]): A pre-configured task queue instance.
- `result_store` (Optional[ResultStorage]): A pre-configured result storage instance.
- `event_store` (Optional[EventStorage]): A pre-configured event storage instance.
- `queues` (Optional[List[str]]): List of queue names to create.
- `worker_type` (Optional[str]): The type of worker to use. One of "async", "thread_pool", "process_pool", "gevent".
- `worker_config` (Optional[Dict[str, Any]]): Configuration for the worker.
- `**kwargs`: Additional keyword arguments passed to the backend or components.

**Examples:**

```python
# Create an OmniQ instance with SQLite backend
from omniq import OmniQ

oq = OmniQ(
    project_name="my_project",
    backend_type="sqlite",
    queues=["high", "medium", "low"]
)
```

```python
# Create an OmniQ instance with pre-configured components
from omniq import OmniQ
from omniq.backends.sqlite import SQLiteBackend

backend = SQLiteBackend(project_name="my_project")
backend.initialize()

oq = OmniQ(
    project_name="my_project",
    backend=backend
)
```

### Class Methods

#### `from_config`

```python
@classmethod
from_config(config: OmniQConfig) -> OmniQ
```

Create an OmniQ instance from a configuration object.

**Parameters:**

- `config` (OmniQConfig): The configuration object.

**Returns:**

- `OmniQ`: A new OmniQ instance.

**Examples:**

```python
from omniq import OmniQ
from omniq.models.config import OmniQConfig, TaskQueueConfig

config = OmniQConfig(
    project_name="my_project",
    task_queue=TaskQueueConfig(
        type="sqlite",
        config={
            "queues": ["high", "medium", "low"]
        }
    )
)

oq = OmniQ.from_config(config)
```

#### `from_config_dict`

```python
@classmethod
from_config_dict(config: Dict[str, Any]) -> OmniQ
```

Create an OmniQ instance from a configuration dictionary.

**Parameters:**

- `config` (Dict[str, Any]): The configuration dictionary.

**Returns:**

- `OmniQ`: A new OmniQ instance.

**Examples:**

```python
from omniq import OmniQ

config = {
    "project_name": "my_project",
    "task_queue": {
        "type": "sqlite",
        "config": {
            "queues": ["high", "medium", "low"]
        }
    }
}

oq = OmniQ.from_config_dict(config)
```

#### `from_config_file`

```python
@classmethod
from_config_file(
    config_path: Union[str, Path],
    env_vars: bool = False,
    **kwargs
) -> OmniQ
```

Create an OmniQ instance from a configuration file.

**Parameters:**

- `config_path` (Union[str, Path]): The path to the configuration file.
- `env_vars` (bool): Whether to substitute environment variables in the configuration.
- `**kwargs`: Additional keyword arguments to override configuration values.

**Returns:**

- `OmniQ`: A new OmniQ instance.

**Examples:**

```python
from omniq import OmniQ

oq = OmniQ.from_config_file("config.yaml")
```

```python
# With environment variable substitution
oq = OmniQ.from_config_file("config.yaml", env_vars=True)
```

```python
# With overrides
oq = OmniQ.from_config_file(
    "config.yaml",
    worker_type="thread_pool",
    worker_config={"max_workers": 4}
)
```

#### `from_env`

```python
@classmethod
from_env(prefix: str = "OMNIQ_") -> OmniQ
```

Create an OmniQ instance from environment variables.

**Parameters:**

- `prefix` (str): The prefix for environment variables.

**Returns:**

- `OmniQ`: A new OmniQ instance.

**Examples:**

```python
from omniq import OmniQ

# Environment variables:
# OMNIQ_PROJECT_NAME=my_project
# OMNIQ_TASK_QUEUE_TYPE=sqlite
# OMNIQ_TASK_QUEUE_CONFIG_QUEUES=high,medium,low

oq = OmniQ.from_env()
```

#### `from_backend`

```python
@classmethod
from_backend(
    backend: Backend,
    result_store_backend: Optional[Backend] = None,
    event_store_backend: Optional[Backend] = None,
    worker_type: Optional[str] = None,
    worker_config: Optional[Dict[str, Any]] = None,
    queues: Optional[List[str]] = None,
    **kwargs
) -> OmniQ
```

Create an OmniQ instance from a backend.

**Parameters:**

- `backend` (Backend): The backend to use for the task queue.
- `result_store_backend` (Optional[Backend]): The backend to use for result storage.
- `event_store_backend` (Optional[Backend]): The backend to use for event storage.
- `worker_type` (Optional[str]): The type of worker to use.
- `worker_config` (Optional[Dict[str, Any]]): Configuration for the worker.
- `queues` (Optional[List[str]]): List of queue names to create.
- `**kwargs`: Additional keyword arguments.

**Returns:**

- `OmniQ`: A new OmniQ instance.

**Examples:**

```python
from omniq import OmniQ
from omniq.backends.sqlite import SQLiteBackend

backend = SQLiteBackend(project_name="my_project")
backend.initialize()

oq = OmniQ.from_backend(
    backend=backend,
    worker_type="thread_pool",
    worker_config={"max_workers": 4},
    queues=["high", "medium", "low"]
)
```

### Instance Methods

#### `enqueue`

```python
enqueue(
    func: Callable,
    func_args: Optional[Dict[str, Any]] = None,
    func_kwargs: Optional[Dict[str, Any]] = None,
    queue_name: str = "default",
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: int = 0,
    run_at: Optional[datetime] = None,
    run_in: Optional[timedelta] = None,
    ttl: Optional[timedelta] = None,
    result_ttl: Optional[timedelta] = None,
    depends_on: Optional[List[str]] = None,
    callback: Optional[Callable] = None,
    callback_args: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_delay: Optional[timedelta] = None,
    store_result: bool = True,
    **kwargs
) -> str
```

Enqueue a task for execution.

**Parameters:**

- `func` (Callable): The function to execute.
- `func_args` (Optional[Dict[str, Any]]): Arguments to pass to the function.
- `func_kwargs` (Optional[Dict[str, Any]]): Keyword arguments to pass to the function.
- `queue_name` (str): The name of the queue to add the task to.
- `name` (Optional[str]): A name for the task.
- `description` (Optional[str]): A description for the task.
- `tags` (Optional[List[str]]): Tags for the task.
- `priority` (int): The priority of the task.
- `run_at` (Optional[datetime]): When to run the task.
- `run_in` (Optional[timedelta]): How long to wait before running the task.
- `ttl` (Optional[timedelta]): Time-to-live for the task.
- `result_ttl` (Optional[timedelta]): Time-to-live for the result.
- `depends_on` (Optional[List[str]]): Task IDs that this task depends on.
- `callback` (Optional[Callable]): Callback function to execute after the task completes.
- `callback_args` (Optional[Dict[str, Any]]): Arguments to pass to the callback.
- `max_retries` (int): Maximum number of retries.
- `retry_delay` (Optional[timedelta]): Delay between retries.
- `store_result` (bool): Whether to store the result.
- `**kwargs`: Additional keyword arguments.

**Returns:**

- `str`: The ID of the enqueued task.

**Examples:**

```python
from omniq import OmniQ
import datetime as dt

def add_numbers(x, y):
    return x + y

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Enqueue a simple task
    task_id = oq.enqueue(
        func=add_numbers,
        func_args={"x": 5, "y": 10}
    )
    
    # Enqueue a task with more options
    task_id = oq.enqueue(
        func=add_numbers,
        func_args={"x": 5, "y": 10},
        queue_name="high",
        name="Add Numbers",
        description="Add two numbers",
        tags=["math", "simple"],
        priority=10,
        run_in=dt.timedelta(seconds=30),
        ttl=dt.timedelta(hours=1),
        result_ttl=dt.timedelta(minutes=30)
    )
```

#### `enqueue_async`

```python
async enqueue_async(
    func: Callable,
    func_args: Optional[Dict[str, Any]] = None,
    func_kwargs: Optional[Dict[str, Any]] = None,
    queue_name: str = "default",
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: int = 0,
    run_at: Optional[datetime] = None,
    run_in: Optional[timedelta] = None,
    ttl: Optional[timedelta] = None,
    result_ttl: Optional[timedelta] = None,
    depends_on: Optional[List[str]] = None,
    callback: Optional[Callable] = None,
    callback_args: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_delay: Optional[timedelta] = None,
    store_result: bool = True,
    **kwargs
) -> str
```

Asynchronously enqueue a task for execution.

**Parameters:**

- Same as `enqueue`.

**Returns:**

- `str`: The ID of the enqueued task.

**Examples:**

```python
import asyncio
from omniq import OmniQ
import datetime as dt

async def async_add_numbers(x, y):
    await asyncio.sleep(0.1)
    return x + y

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Enqueue a simple async task
        task_id = await oq.enqueue_async(
            func=async_add_numbers,
            func_args={"x": 5, "y": 10}
        )
        
        # Enqueue a task with more options
        task_id = await oq.enqueue_async(
            func=async_add_numbers,
            func_args={"x": 5, "y": 10},
            queue_name="high",
            name="Add Numbers",
            description="Add two numbers asynchronously",
            tags=["math", "async"],
            priority=10,
            run_in=dt.timedelta(seconds=30),
            ttl=dt.timedelta(hours=1),
            result_ttl=dt.timedelta(minutes=30)
        )

asyncio.run(main())
```

#### `schedule`

```python
schedule(
    func: Callable,
    func_args: Optional[Dict[str, Any]] = None,
    func_kwargs: Optional[Dict[str, Any]] = None,
    queue_name: str = "default",
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: int = 0,
    schedule_type: str = "interval",
    cron_expression: Optional[str] = None,
    interval: Optional[timedelta] = None,
    run_at: Optional[datetime] = None,
    max_runs: Optional[int] = None,
    ttl: Optional[timedelta] = None,
    result_ttl: Optional[timedelta] = None,
    depends_on: Optional[List[str]] = None,
    callback: Optional[Callable] = None,
    callback_args: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_delay: Optional[timedelta] = None,
    store_result: bool = True,
    **kwargs
) -> str
```

Schedule a recurring task.

**Parameters:**

- `func` (Callable): The function to execute.
- `func_args` (Optional[Dict[str, Any]]): Arguments to pass to the function.
- `func_kwargs` (Optional[Dict[str, Any]]): Keyword arguments to pass to the function.
- `queue_name` (str): The name of the queue to add the task to.
- `name` (Optional[str]): A name for the schedule.
- `description` (Optional[str]): A description for the schedule.
- `tags` (Optional[List[str]]): Tags for the schedule.
- `priority` (int): The priority of the task.
- `schedule_type` (str): The type of schedule. One of "interval", "cron", "run_at".
- `cron_expression` (Optional[str]): Cron expression for the schedule.
- `interval` (Optional[timedelta]): Interval between runs.
- `run_at` (Optional[datetime]): When to run the task.
- `max_runs` (Optional[int]): Maximum number of runs.
- `ttl` (Optional[timedelta]): Time-to-live for the task.
- `result_ttl` (Optional[timedelta]): Time-to-live for the result.
- `depends_on` (Optional[List[str]]): Task IDs that this task depends on.
- `callback` (Optional[Callable]): Callback function to execute after the task completes.
- `callback_args` (Optional[Dict[str, Any]]): Arguments to pass to the callback.
- `max_retries` (int): Maximum number of retries.
- `retry_delay` (Optional[timedelta]): Delay between retries.
- `store_result` (bool): Whether to store the result.
- `**kwargs`: Additional keyword arguments.

**Returns:**

- `str`: The ID of the schedule.

**Examples:**

```python
from omniq import OmniQ
import datetime as dt

def send_email(recipient, subject, body):
    # Send email logic
    return f"Email sent to {recipient}"

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Schedule a task to run every hour
    schedule_id = oq.schedule(
        func=send_email,
        func_args={
            "recipient": "user@example.com",
            "subject": "Hourly Report",
            "body": "This is your hourly report."
        },
        interval=dt.timedelta(hours=1),
        name="Hourly Email",
        description="Send an hourly email report"
    )
    
    # Schedule a task using a cron expression
    schedule_id = oq.schedule(
        func=send_email,
        func_args={
            "recipient": "admin@example.com",
            "subject": "Daily Report",
            "body": "This is your daily report."
        },
        cron_expression="0 9 * * *",  # Every day at 9 AM
        name="Daily Email",
        description="Send a daily email report"
    )
```

#### `schedule_async`

```python
async schedule_async(
    func: Callable,
    func_args: Optional[Dict[str, Any]] = None,
    func_kwargs: Optional[Dict[str, Any]] = None,
    queue_name: str = "default",
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: int = 0,
    schedule_type: str = "interval",
    cron_expression: Optional[str] = None,
    interval: Optional[timedelta] = None,
    run_at: Optional[datetime] = None,
    max_runs: Optional[int] = None,
    ttl: Optional[timedelta] = None,
    result_ttl: Optional[timedelta] = None,
    depends_on: Optional[List[str]] = None,
    callback: Optional[Callable] = None,
    callback_args: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_delay: Optional[timedelta] = None,
    store_result: bool = True,
    **kwargs
) -> str
```

Asynchronously schedule a recurring task.

**Parameters:**

- Same as `schedule`.

**Returns:**

- `str`: The ID of the schedule.

**Examples:**

```python
import asyncio
from omniq import OmniQ
import datetime as dt

async def async_send_email(recipient, subject, body):
    await asyncio.sleep(0.1)  # Simulate async work
    return f"Email sent to {recipient}"

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Schedule a task to run every hour
        schedule_id = await oq.schedule_async(
            func=async_send_email,
            func_args={
                "recipient": "user@example.com",
                "subject": "Hourly Report",
                "body": "This is your hourly report."
            },
            interval=dt.timedelta(hours=1),
            name="Hourly Email",
            description="Send an hourly email report"
        )

asyncio.run(main())
```

#### `get_result`

```python
get_result(
    task_id: str,
    timeout: Optional[float] = None,
    poll_interval: float = 0.1
) -> Any
```

Get the result of a task.

**Parameters:**

- `task_id` (str): The ID of the task.
- `timeout` (Optional[float]): Maximum time to wait for the result.
- `poll_interval` (float): Interval between polling for the result.

**Returns:**

- `Any`: The result of the task.

**Raises:**

- `TimeoutError`: If the timeout is reached.
- `TaskNotFoundError`: If the task is not found.
- `TaskFailedError`: If the task failed.

**Examples:**

```python
from omniq import OmniQ

def add_numbers(x, y):
    return x + y

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    oq.start_worker(worker_type="thread_pool", max_workers=1)
    
    try:
        # Enqueue a task
        task_id = oq.enqueue(
            func=add_numbers,
            func_args={"x": 5, "y": 10}
        )
        
        # Get the result
        result = oq.get_result(task_id)
        print(f"Result: {result}")  # Output: Result: 15
        
        # Get the result with a timeout
        result = oq.get_result(task_id, timeout=10.0)
        print(f"Result: {result}")
        
    finally:
        oq.stop_worker()
```

#### `get_result_async`

```python
async get_result_async(
    task_id: str,
    timeout: Optional[float] = None,
    poll_interval: float = 0.1
) -> Any
```

Asynchronously get the result of a task.

**Parameters:**

- Same as `get_result`.

**Returns:**

- `Any`: The result of the task.

**Raises:**

- Same as `get_result`.

**Examples:**

```python
import asyncio
from omniq import OmniQ

async def async_add_numbers(x, y):
    await asyncio.sleep(0.1)
    return x + y

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        await oq.start_worker_async(worker_type="async", max_workers=1)
        
        try:
            # Enqueue a task
            task_id = await oq.enqueue_async(
                func=async_add_numbers,
                func_args={"x": 5, "y": 10}
            )
            
            # Get the result
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")  # Output: Result: 15
            
        finally:
            await oq.stop_worker_async()

asyncio.run(main())
```

#### `get_task`

```python
get_task(task_id: str) -> Optional[Task]
```

Get a task by ID.

**Parameters:**

- `task_id` (str): The ID of the task.

**Returns:**

- `Optional[Task]`: The task, or None if not found.

**Examples:**

```python
from omniq import OmniQ

def add_numbers(x, y):
    return x + y

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Enqueue a task
    task_id = oq.enqueue(
        func=add_numbers,
        func_args={"x": 5, "y": 10}
    )
    
    # Get the task
    task = oq.get_task(task_id)
    if task:
        print(f"Task ID: {task.id}")
        print(f"Task status: {task.status}")
        print(f"Task function: {task.func}")
```

#### `get_task_async`

```python
async get_task_async(task_id: str) -> Optional[Task]
```

Asynchronously get a task by ID.

**Parameters:**

- Same as `get_task`.

**Returns:**

- `Optional[Task]`: The task, or None if not found.

**Examples:**

```python
import asyncio
from omniq import OmniQ

async def async_add_numbers(x, y):
    await asyncio.sleep(0.1)
    return x + y

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Enqueue a task
        task_id = await oq.enqueue_async(
            func=async_add_numbers,
            func_args={"x": 5, "y": 10}
        )
        
        # Get the task
        task = await oq.get_task_async(task_id)
        if task:
            print(f"Task ID: {task.id}")
            print(f"Task status: {task.status}")
            print(f"Task function: {task.func}")

asyncio.run(main())
```

#### `get_schedule`

```python
get_schedule(schedule_id: str) -> Optional[Schedule]
```

Get a schedule by ID.

**Parameters:**

- `schedule_id` (str): The ID of the schedule.

**Returns:**

- `Optional[Schedule]`: The schedule, or None if not found.

**Examples:**

```python
from omniq import OmniQ
import datetime as dt

def send_email(recipient, subject, body):
    return f"Email sent to {recipient}"

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Schedule a task
    schedule_id = oq.schedule(
        func=send_email,
        func_args={
            "recipient": "user@example.com",
            "subject": "Test Email",
            "body": "This is a test email."
        },
        interval=dt.timedelta(hours=1),
        name="Test Schedule"
    )
    
    # Get the schedule
    schedule = oq.get_schedule(schedule_id)
    if schedule:
        print(f"Schedule ID: {schedule.id}")
        print(f"Schedule status: {schedule.status}")
        print(f"Schedule interval: {schedule.interval}")
```

#### `get_schedule_async`

```python
async get_schedule_async(schedule_id: str) -> Optional[Schedule]
```

Asynchronously get a schedule by ID.

**Parameters:**

- Same as `get_schedule`.

**Returns:**

- `Optional[Schedule]`: The schedule, or None if not found.

**Examples:**

```python
import asyncio
from omniq import OmniQ
import datetime as dt

async def async_send_email(recipient, subject, body):
    await asyncio.sleep(0.1)
    return f"Email sent to {recipient}"

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Schedule a task
        schedule_id = await oq.schedule_async(
            func=async_send_email,
            func_args={
                "recipient": "user@example.com",
                "subject": "Test Email",
                "body": "This is a test email."
            },
            interval=dt.timedelta(hours=1),
            name="Test Schedule"
        )
        
        # Get the schedule
        schedule = await oq.get_schedule_async(schedule_id)
        if schedule:
            print(f"Schedule ID: {schedule.id}")
            print(f"Schedule status: {schedule.status}")
            print(f"Schedule interval: {schedule.interval}")

asyncio.run(main())
```

#### `start_worker`

```python
start_worker(
    worker_type: Optional[str] = None,
    worker_config: Optional[Dict[str, Any]] = None
) -> None
```

Start a worker.

**Parameters:**

- `worker_type` (Optional[str]): The type of worker to start.
- `worker_config` (Optional[Dict[str, Any]]): Configuration for the worker.

**Examples:**

```python
from omniq import OmniQ

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Start a thread pool worker
    oq.start_worker(worker_type="thread_pool", worker_config={"max_workers": 4})
    
    try:
        # Enqueue and process tasks
        task_id = oq.enqueue(func=lambda: "Hello, World!")
        result = oq.get_result(task_id)
        print(f"Result: {result}")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

#### `start_worker_async`

```python
async start_worker_async(
    worker_type: Optional[str] = None,
    worker_config: Optional[Dict[str, Any]] = None
) -> None
```

Asynchronously start a worker.

**Parameters:**

- Same as `start_worker`.

**Examples:**

```python
import asyncio
from omniq import OmniQ

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Start an async worker
        await oq.start_worker_async(worker_type="async", worker_config={"max_workers": 4})
        
        try:
            # Enqueue and process tasks
            task_id = await oq.enqueue_async(func=lambda: "Hello, World!")
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

asyncio.run(main())
```

#### `stop_worker`

```python
stop_worker() -> None
```

Stop the worker.

**Examples:**

```python
from omniq import OmniQ

with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    # Start a worker
    oq.start_worker(worker_type="thread_pool", max_workers=4)
    
    try:
        # Enqueue and process tasks
        task_id = oq.enqueue(func=lambda: "Hello, World!")
        result = oq.get_result(task_id)
        print(f"Result: {result}")
        
    finally:
        # Stop the worker
        oq.stop_worker()
```

#### `stop_worker_async`

```python
async stop_worker_async() -> None
```

Asynchronously stop the worker.

**Examples:**

```python
import asyncio
from omniq import OmniQ

async def main():
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        # Start a worker
        await oq.start_worker_async(worker_type="async", max_workers=4)
        
        try:
            # Enqueue and process tasks
            task_id = await oq.enqueue_async(func=lambda: "Hello, World!")
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")
            
        finally:
            # Stop the worker
            await oq.stop_worker_async()

asyncio.run(main())
```

### Context Manager

OmniQ can be used as a context manager to ensure proper initialization and cleanup:

```python
from omniq import OmniQ

# Using as a context manager
with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
    oq.start_worker(worker_type="thread_pool", max_workers=2)
    
    try:
        # Enqueue and process tasks
        task_id = oq.enqueue(func=lambda: "Hello, World!")
        result = oq.get_result(task_id)
        print(f"Result: {result}")
        
    finally:
        oq.stop_worker()
```

For async operations, use the async context manager:

```python
import asyncio
from omniq import OmniQ

async def main():
    # Using as an async context manager
    async with OmniQ(project_name="my_project", backend_type="sqlite") as oq:
        await oq.start_worker_async(worker_type="async", max_workers=2)
        
        try:
            # Enqueue and process tasks
            task_id = await oq.enqueue_async(func=lambda: "Hello, World!")
            result = await oq.get_result_async(task_id)
            print(f"Result: {result}")
            
        finally:
            await oq.stop_worker_async()

asyncio.run(main())
```

## Next Steps

For more detailed information about specific components, see:

- [Models API](models.qmd) - Documentation for data models
- [Backends API](backends.qmd) - Documentation for storage backends
- [Storage API](storage.qmd) - Documentation for storage components
- [Workers API](workers.qmd) - Documentation for worker components
- [Serialization API](serialization.qmd) - Documentation for serialization components
```

### 5.8 Contributing Guide (`docs/contributing.qmd`)

**Purpose**: Provide guidelines for contributing to OmniQ.

**Implementation Requirements**:
- Explain how to set up a development environment
- Describe the contribution process
- Include coding standards and guidelines
- Provide information about testing and documentation

**Code Structure**:
```markdown
---
title: Contributing
---

# Contributing to OmniQ

Thank you for your interest in contributing to OmniQ! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Process](#contributing-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- A GitHub account

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally

```bash
git clone https://github.com/your-username/omniq.git
cd omniq
```

3. Add the original repository as a remote

```bash
git remote add upstream https://github.com/original-org/omniq.git
```

## Development Setup

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver. It's the recommended way to set up the development environment.

1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install the project in development mode

```bash
uv pip install -e ".[dev]"
```

### Using pip

If you prefer to use pip:

1. Create a virtual environment

```bash
python -m venv omniq-dev
source omniq-dev/bin/activate  # On Windows: omniq-dev\Scripts\activate
```

2. Install the project in development mode

```bash
pip install -e ".[dev]"
```

### Verify Installation

To verify that your development environment is set up correctly:

```bash
python -c "import omniq; print(omniq.__version__)"
```

You should see the version number of OmniQ.

## Contributing Process

### 1. Find an Issue

Look for issues labeled "good first issue" or "help wanted" in the [issue tracker](https://github.com/original-org/omniq/issues). If you have an idea for a new feature or improvement, please [create an issue](#reporting-issues) to discuss it first.

### 2. Create a Branch

Create a new branch for your contribution:

```bash
git checkout -b feature/your-feature-name
```

or for a bug fix:

```bash
git checkout -b fix/your-fix-name
```

### 3. Make Changes

Make your changes to the codebase. Follow the [coding standards](#coding-standards) and ensure that your changes are well-tested.

### 4. Test Your Changes

Run the test suite to ensure that your changes don't break existing functionality:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src/omniq
```

### 5. Update Documentation

If your changes affect the public API or add new features, update the documentation:

```bash
cd docs
quarto render
```

### 6. Commit Your Changes

Commit your changes with a clear and descriptive commit message:

```bash
git add .
git commit -m "Add new feature: description of the feature"
```

### 7. Push Your Changes

Push your changes to your fork:

```bash
git push origin feature/your-feature-name
```

### 8. Create a Pull Request

Create a pull request to the original repository. In your pull request:

- Describe your changes in detail
- Reference any related issues
- Include screenshots if your changes affect the UI
- Ensure that all checks pass

## Coding Standards

### Python Style

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code style. We use the following tools to enforce code quality:

- [Black](https://black.readthedocs.io/) for code formatting
- [isort](https://pycqa.github.io/isort/) for import sorting
- [Ruff](https://github.com/charliermarsh/ruff) for linting
- [MyPy](https://mypy.readthedocs.io/) for type checking

### Formatting Code

Before committing your changes, format your code:

```bash
black src/ tests/
isort src/ tests/
```

### Linting Code

Lint your code to catch potential issues:

```bash
ruff check src/ tests/
```

### Type Checking

Check your code for type errors:

```bash
mypy src/
```

### Docstrings

We use [Google-style docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) for documentation. All public functions, classes, and methods should have docstrings.

Example:

```python
def add_numbers(x: int, y: int) -> int:
    """Add two numbers and return the result.

    Args:
        x: The first number.
        y: The second number.

    Returns:
        The sum of the two numbers.
    """
    return x + y
```

### Type Hints

All public functions, classes, and methods should have type hints. Use the `typing` module for complex types.

Example:

```python
from typing import Dict, List, Optional

def process_data(data: Dict[str, List[int]], threshold: Optional[int] = None) -> List[str]:
    """Process data and return a list of strings.

    Args:
        data: A dictionary mapping strings to lists of integers.
        threshold: An optional threshold value.

    Returns:
        A list of strings representing the processed data.
    """
    # Implementation
    pass
```

## Testing

### Test Structure

Tests are organized in the `tests/` directory, mirroring the structure of the `src/` directory:

```
tests/
├── unit/          # Unit tests
│   ├── models/    # Tests for models
│   ├── storage/   # Tests for storage components
│   └── workers/   # Tests for worker components
├── integration/   # Integration tests
└── performance/   # Performance tests
```

### Writing Tests

We use [pytest](https://pytest.org/) for testing. Tests should be:

- **Descriptive**: Use clear and descriptive test names
- **Isolated**: Each test should be independent of others
- **Comprehensive**: Cover happy paths, error cases, and edge cases
- **Fast**: Unit tests should be fast to run

Example:

```python
def test_add_numbers():
    """Test that add_numbers correctly adds two numbers."""
    from omniq.examples.math import add_numbers
    
    result = add_numbers(2, 3)
    assert result == 5
```

### Running Tests

Run all tests:

```bash
pytest
```

Run specific tests:

```bash
pytest tests/unit/models/test_task.py
```

Run tests with coverage:

```bash
pytest --cov=src/omniq
```

Run tests with coverage and generate an HTML report:

```bash
pytest --cov=src/omniq --cov-report=html
```

### Test Coverage

We aim for a minimum of 80% test coverage. You can check the coverage of your changes:

```bash
pytest --cov=src/omniq --cov-report=term-missing
```

## Documentation

### Documentation Structure

Documentation is written in [Quarto](https://quarto.org/) and located in the `docs/` directory:

```
docs/
├── _quarto.yml          # Quarto configuration
├── index.qmd            # Home page
├── installation.qmd     # Installation guide
├── quickstart.qmd       # Quick start guide
├── user_guide/          # User guides
├── api/                 # API reference
├── examples/            # Examples and tutorials
└── contributing.qmd     # Contributing guide
```

### Writing Documentation

Documentation should be:

- **Clear**: Use simple and clear language
- **Comprehensive**: Cover all features and use cases
- **Accurate**: Ensure that code examples work as described
- **Up-to-date**: Keep documentation in sync with code changes

### Building Documentation

Build the documentation:

```bash
cd docs
quarto render
```

The built documentation will be in the `docs/_site/` directory.

### Previewing Documentation

Preview the documentation while editing:

```bash
cd docs
quarto preview
```

This will start a local web server and open the documentation in your browser.

## Submitting Changes

### Pull Request Process

1. Ensure that your code follows the [coding standards](#coding-standards)
2. Ensure that all tests pass
3. Ensure that documentation is updated if necessary
4. Update the [CHANGELOG.md](CHANGELOG.md) if your changes introduce new features or breaking changes
5. Create a pull request with a clear title and description
6. Link to any related issues in the pull request description
7. Wait for the pull request to be reviewed and approved

### Pull Request Template

When creating a pull request, use the following template:

```markdown
## Description

A clear and concise description of the changes.

## Type of Change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?

Please describe the tests that you ran to verify your changes.

## Checklist:

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published in downstream modules
```

## Reporting Issues

### Bug Reports

When reporting a bug, please include:

- A clear and descriptive title
- A detailed description of the bug
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Environment information (Python version, OS, etc.)
- Any relevant error messages or stack traces

### Feature Requests

When requesting a new feature, please include:

- A clear and descriptive title
- A detailed description of the feature
- The problem that the feature would solve
- Any alternative solutions or features you've considered
- Any examples or mockups of how the feature would work

### Issue Template

When creating an issue, use the appropriate template:

#### Bug Report

```markdown
## Bug Description

A clear and concise description of the bug.

## Steps to Reproduce

Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

A clear and concise description of what actually happened.

## Environment

- OS: [e.g. Ubuntu 20.04]
- Python version: [e.g. 3.9.0]
- OmniQ version: [e.g. 0.1.0]

## Additional Context

Add any other context about the problem here.
```

#### Feature Request

```markdown
## Feature Description

A clear and concise description of the feature.

## Problem Statement

What problem would this feature solve?

## Proposed Solution

Describe the solution you'd like.

## Alternative Solutions

Describe any alternative solutions or features you've considered.

## Additional Context

Add any other context or screenshots about the feature request here.
```

## Getting Help

If you need help with contributing or have questions about the codebase:

- Check the [documentation](https://omniq.readthedocs.io)
- Search existing [issues](https://github.com/original-org/omniq/issues)
- Create a new issue with the "question" label

## Community

Join our community to connect with other contributors and users:

- [Discussions](https://github.com/original-org/omniq/discussions)
- [Discord/Slack](link to chat platform)

Thank you for contributing to OmniQ!
```

## Implementation Notes

### Documentation Strategy

The documentation follows a comprehensive strategy:

1. **User-Focused**: Organized around user needs and tasks
2. **Progressive**: Starts with simple concepts and progresses to advanced topics
3. **Comprehensive**: Covers all features and use cases
4. **Practical**: Includes plenty of examples and code snippets
5. **Accessible**: Uses clear language and visual aids

### Documentation Quality

All documentation follows these quality guidelines:

1. **Accuracy**: Code examples are tested and verified
2. **Completeness**: All public APIs are documented
3. **Clarity**: Explanations are clear and easy to understand
4. **Consistency**: Formatting and style are consistent across all documents
5. **Maintainability**: Documentation is easy to update and maintain

### Documentation Tools

The documentation uses modern tools for a professional result:

1. **Quarto**: For authoring and publishing
2. **Mermaid**: For diagrams and visualizations
3. **GitHub**: For hosting and collaboration
4. **Read the Docs**: for public hosting (optional)

## Documentation Strategy

For Task 5, the following strategy is used:

1. **User-Centric Organization**: Documentation is organized around user needs
2. **Progressive Learning**: Starts with basics and progresses to advanced topics
3. **Comprehensive Coverage**: Covers all features and use cases
4. **Practical Examples**: Includes plenty of working examples
5. **Professional Presentation**: Uses modern tools for a polished result

## Dependencies

Task 5 requires the following dependencies:

- Documentation: `quarto`, `mermaid`
- Development: Same as Tasks 1-4

## Deliverables

1. Complete Quarto project structure
2. User guides for all major features
3. Comprehensive API reference
4. Examples and tutorials
5. Contributing guidelines
6. Professional HTML documentation output