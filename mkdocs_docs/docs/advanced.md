# Advanced Usage

OmniQ is designed with flexibility in mind, offering advanced configuration options and features to handle complex, real-world scenarios. This guide covers some of the more sophisticated capabilities, including advanced configuration, handling mixed synchronous and asynchronous tasks, and integrating with cloud storage solutions.

## Configuration-Based Setup

While you can instantiate OmniQ components directly, a configuration-driven approach offers greater flexibility, especially in production environments. This allows you to define your setup in YAML files, dictionaries, or even environment variables, decoupling your application logic from your infrastructure setup.

### Using a YAML Configuration File

For maximum clarity and maintainability, we recommend using a YAML file to define your OmniQ setup. This approach allows you to specify the project name, task queue, result store, and worker settings in a single, easy-to-read file.

Here's an example of a `config.yaml` file:

```yaml
project_name: production_app

task_queue:
  type: file
  config:
    base_dir: ./omniq_data/tasks
    queues:
      - high_priority
      - default
      - low_priority

result_store:
  type: sqlite
  config:
    base_dir: ./omniq_data/results

worker:
  type: thread_pool
  config:
    max_workers: 10
```

You can then load this configuration and create an `OmniQ` instance with a single command:

```python
from omniq import OmniQ

# Load the configuration from the YAML file
oq = OmniQ.from_config_file("config.yaml")

# Now your OmniQ instance is ready to use
with oq:
    # Enqueue tasks, manage workers, etc.
    pass
```

### Using Environment Variables

For cloud-native applications and CI/CD pipelines, you can override configuration settings using environment variables. OmniQ recognizes variables prefixed with `OMNIQ_`.

For example, to override the worker's `max_workers` setting, you can set the following environment variable:

```bash
export OMNIQ_WORKER_CONFIG_MAX_WORKERS=20
```

For more details on configuration loading and precedence, see the API reference under Configuration.

## Handling Sync and Async Tasks

Modern applications often require a mix of synchronous (CPU-bound) and asynchronous (I/O-bound) tasks. OmniQ's workers are designed to handle both types of tasks seamlessly within the same queue, simplifying your architecture.

Both `ThreadWorker` and `AsyncWorker` can execute sync and async functions without any special configuration. The worker automatically detects whether a task function is a coroutine and executes it accordingly.

```python
import asyncio
import time
from omniq import OmniQ
from omniq.queue import FileTaskQueue

# A standard synchronous function
def sync_task(x, y):
    print(f"Executing sync task: {x} * {y}")
    time.sleep(0.1)
    return x * y

# An asynchronous function
async def async_task(x, y):
    print(f"Executing async task: {x} + {y}")
    await asyncio.sleep(0.1)
    return x + y

# Setup OmniQ (can be done via config file as well)
oq = OmniQ(project_name="mixed_tasks_example")

with oq:
    # Enqueue both types of tasks
    sync_task_id = oq.enqueue(sync_task, func_args={'x': 5, 'y': 10})
    async_task_id = oq.enqueue(async_task, func_args={'x': 5, 'y': 10})

    # Wait for results
    time.sleep(1)

    # Retrieve results - the worker handles both correctly
    sync_result = oq.get_result(sync_task_id)    # -> 50
    async_result = oq.get_result(async_task_id) # -> 15

    print(f"Sync Result: {sync_result}")
    print(f"Async Result: {async_result}")
```

## Cloud Storage with `fsspec`

OmniQ's `FileTaskQueue` and `FileResultStorage` components are built on top of the `fsspec` (Filesystem Spec) library. This powerful abstraction allows you to use virtually any storage backend that `fsspec` supports, including cloud storage providers like Amazon S3, Google Cloud Storage (GCS), and Azure Blob Storage.

To use a cloud storage backend, simply provide the appropriate URI in the `base_dir` and include any necessary credentials in the `storage_options` dictionary.

### Example: Using Amazon S3

First, ensure you have the required library installed:

```bash
pip install s3fs
```

Then, configure the `FileTaskQueue` to use an S3 bucket:

```python
from omniq.queue import FileTaskQueue

# Configuration for S3 storage
s3_queue = FileTaskQueue(
    project_name="s3_demo",
    base_dir="s3://your-cool-bucket/omniq/tasks",
    storage_options={
        "key": "YOUR_AWS_ACCESS_KEY_ID",
        "secret": "YOUR_AWS_SECRET_ACCESS_KEY",
    }
)

# You can now use this queue with your OmniQ instance
# oq = OmniQ(project_name="s3_demo", task_queue=s3_queue, ...)
```

The same principle applies to `FileResultStorage` and other cloud providers like GCS (`gs://...`) and Azure Blob Storage (`abfs://...`).

## Performance Tips

- Choose the Right Worker: Use `ThreadWorker` for I/O-bound synchronous tasks. For `async` tasks, `AsyncWorker` is generally more efficient as it can handle thousands of concurrent operations with a small number of threads.
- Serialization: The default serializer (`dill`) is very flexible but may not be the fastest. For performance-critical applications with well-defined data structures, consider using a faster serializer like `msgspec`.
- Batching: When enqueuing a large number of tasks, consider using `enqueue_many` to reduce the overhead of individual network requests or disk I/O operations.
- Persistent Connections: When using network-based backends (like Redis or a database), ensure your application manages connections efficiently. OmniQ's built-in components handle this, but be mindful if you create custom components.