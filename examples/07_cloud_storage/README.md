# Using fsspec for Cloud Storage

This example demonstrates how to use `fsspec` with OmniQ's [`FileTaskQueue`](../../src/omniq/queue/base.py:1) and [`FileResultStorage`](../../src/omniq/results/base.py:1) to connect to various storage backends including local files, in-memory storage, and cloud storage providers like S3, Azure Blob Storage, and Google Cloud Storage.

## Overview

OmniQ leverages the [`fsspec`](https://filesystem-spec.readthedocs.io/) library to provide a unified interface for different storage backends. This allows you to seamlessly switch between local development and cloud production environments without changing your code structure.

## Supported Storage Backends

### Local and Memory Storage (No additional dependencies)
- **Local filesystem**: Standard file system operations
- **Memory filesystem**: In-memory storage for testing and development

### Cloud Storage (Requires optional dependencies)
- **Amazon S3**: Requires [`s3fs`](https://s3fs.readthedocs.io/) package
- **Azure Blob Storage**: Requires [`adlfs`](https://github.com/fsspec/adlfs) package  
- **Google Cloud Storage**: Requires [`gcsfs`](https://gcsfs.readthedocs.io/) package

## Installation

For cloud storage support, install the optional dependencies:

```bash
# For S3 support
uv add s3fs

# For Azure Blob Storage support
uv add adlfs

# For Google Cloud Storage support
uv add gcsfs

# Or install all cloud storage dependencies
uv add s3fs adlfs gcsfs
```

## Basic Usage

### Local Filesystem

```python
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# Create queue and result storage using local filesystem
queue = FileTaskQueue(
    project_name="my_project",
    base_dir="/path/to/local/storage",
    queues=["high", "medium", "low"]
)

result_store = FileResultStorage(
    project_name="my_project", 
    base_dir="/path/to/local/storage/results"
)
```

### Memory Filesystem

```python
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# Create queue and result storage using memory filesystem
queue = FileTaskQueue(
    project_name="my_project",
    base_dir="memory://my_project",
    queues=["high", "medium", "low"]
)

result_store = FileResultStorage(
    project_name="my_project",
    base_dir="memory://my_project/results"
)
```

## Cloud Storage Configuration

### Amazon S3

```python
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# S3 configuration with credentials
s3_queue = FileTaskQueue(
    project_name="my_project",
    base_dir="s3://my-bucket/omniq",
    queues=["high", "medium", "low"],
    storage_options={
        "key": "your_access_key_id",
        "secret": "your_secret_access_key",
        "region": "us-east-1"  # Optional
    }
)

s3_results = FileResultStorage(
    project_name="my_project",
    base_dir="s3://my-bucket/omniq/results",
    storage_options={
        "key": "your_access_key_id", 
        "secret": "your_secret_access_key",
        "region": "us-east-1"
    }
)
```

### Azure Blob Storage

```python
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# Azure Blob Storage configuration
azure_queue = FileTaskQueue(
    project_name="my_project",
    base_dir="abfs://my-container/omniq",
    queues=["high", "medium", "low"],
    storage_options={
        "account_name": "mystorageaccount",
        "account_key": "your_account_key"
        # Alternative: "sas_token": "your_sas_token"
    }
)

azure_results = FileResultStorage(
    project_name="my_project",
    base_dir="abfs://my-container/omniq/results",
    storage_options={
        "account_name": "mystorageaccount",
        "account_key": "your_account_key"
    }
)
```

### Google Cloud Storage

```python
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# Google Cloud Storage configuration
gcs_queue = FileTaskQueue(
    project_name="my_project",
    base_dir="gs://my-bucket/omniq",
    queues=["high", "medium", "low"],
    storage_options={
        "token": "/path/to/service-account.json"
        # Alternative: "token": "cloud" for default credentials
    }
)

gcs_results = FileResultStorage(
    project_name="my_project",
    base_dir="gs://my-bucket/omniq/results",
    storage_options={
        "token": "/path/to/service-account.json"
    }
)
```

## Complete Example with OmniQ

```python
from omniq import OmniQ
from omniq.queue import FileTaskQueue
from omniq.results import FileResultStorage

# Create OmniQ instance with cloud storage
oq = OmniQ(
    project_name="my_project",
    task_queue=FileTaskQueue(
        project_name="my_project",
        base_dir="s3://my-bucket/omniq/tasks",
        queues=["high", "medium", "low"],
        storage_options={"key": "access_key", "secret": "secret_key"}
    ),
    result_store=FileResultStorage(
        project_name="my_project",
        base_dir="s3://my-bucket/omniq/results",
        storage_options={"key": "access_key", "secret": "secret_key"}
    )
)

# Define a task
def process_data(data):
    return f"Processed: {data}"

# Use OmniQ normally - storage backend is transparent
with oq:
    task_id = oq.enqueue(process_data, func_args={"data": "sample data"})
    result = oq.get_result(task_id)
    print(result)  # "Processed: sample data"
```

## Environment Variables

You can also configure storage backends using environment variables:

```bash
# For S3
export OMNIQ_FSSPEC_URI="s3://my-bucket/omniq"
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"

# For Azure
export OMNIQ_FSSPEC_URI="abfs://my-container/omniq"
export AZURE_STORAGE_ACCOUNT_NAME="mystorageaccount"
export AZURE_STORAGE_ACCOUNT_KEY="your_account_key"

# For GCS
export OMNIQ_FSSPEC_URI="gs://my-bucket/omniq"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## Files in this Example

- [`cloud_storage.py`](cloud_storage.py:1): Complete Python script demonstrating fsspec usage with runnable local/memory examples and commented cloud examples
- [`cloud_storage.ipynb`](cloud_storage.ipynb:1): Interactive Jupyter notebook with step-by-step demonstrations
- [`README.md`](README.md:1): This documentation file

## Key Benefits

1. **Unified Interface**: Same API regardless of storage backend
2. **Easy Migration**: Switch from local to cloud storage with minimal code changes
3. **Development Flexibility**: Use memory storage for testing, local for development, cloud for production
4. **Cost Optimization**: Choose the most cost-effective storage solution for your use case
5. **Scalability**: Leverage cloud storage for distributed and high-volume workloads

## Best Practices

1. **Credentials Management**: Use environment variables or credential files instead of hardcoding secrets
2. **Region Selection**: Choose storage regions close to your compute resources for better performance
3. **Bucket/Container Naming**: Use descriptive names and follow cloud provider naming conventions
4. **Access Control**: Configure appropriate IAM policies and access controls
5. **Monitoring**: Set up monitoring and alerting for storage operations
6. **Backup Strategy**: Implement appropriate backup and disaster recovery strategies

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Verify credentials and permissions
2. **Network Connectivity**: Check firewall rules and network access
3. **Bucket/Container Access**: Ensure proper read/write permissions
4. **Region Mismatches**: Verify storage region configuration
5. **Dependency Issues**: Ensure required packages (s3fs, adlfs, gcsfs) are installed

### Debug Mode

Enable debug logging to troubleshoot fsspec operations:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your OmniQ code here
```

This will provide detailed information about fsspec operations and help identify issues.