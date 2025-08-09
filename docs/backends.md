# Backends

OmniQ's architecture is designed to be highly modular, allowing different components (task queues, result storage, event storage) to utilize various backends independently. A "backend" in OmniQ refers to the underlying technology or system used for data persistence and communication.

## Key Principles of Backends

*   **Interchangeability**: You can swap out one backend for another with minimal changes to your application code, typically just by updating configuration.
*   **Decoupling**: Each component can use a different backend. For example, your task queue might use Redis for high-throughput queuing, while results are stored in PostgreSQL for robust persistence.
*   **Abstraction**: OmniQ provides a unified interface for interacting with different backends, abstracting away the underlying implementation details.

## Supported Backend Types

OmniQ supports a variety of backend types, each suitable for different use cases:

### File-based Backends

*   **File (via `fsspec`)**:
    *   **Description**: Stores data in files on a local filesystem or integrates with cloud storage services (S3, Azure, GCP) through `fsspec`.
    *   **Use Cases**: Simple persistence, local development, small-scale deployments, or leveraging existing cloud storage infrastructure.
    *   **Configuration**:
        ```yaml
        # Example for task queue using file backend
        task_queue:
          type: file
          base_dir: ./data/tasks
        ```

*   **SQLite**:
    *   **Description**: A self-contained, serverless, zero-configuration, transactional SQL database engine. Stores data in a single file.
    *   **Use Cases**: Embedded databases, local persistence, small to medium-sized applications where a full database server is overkill.
    *   **Configuration**:
        ```yaml
        # Example for result storage using SQLite backend
        result_storage:
          type: sqlite
          database_path: ./data/results.db
        ```

### Database Backends

*   **PostgreSQL**:
    *   **Description**: A powerful, open-source object-relational database system known for its reliability, feature robustness, and performance.
    *   **Use Cases**: Production environments, large-scale applications, complex data relationships, high concurrency.
    *   **Configuration**:
        ```yaml
        # Example for event storage using PostgreSQL backend
        event_storage:
          type: postgres
          dsn: postgresql://user:password@host:port/database_name
        ```

### Messaging/In-Memory Backends

*   **Redis**:
    *   **Description**: An open-source, in-memory data structure store, used as a database, cache, and message broker.
    *   **Use Cases**: High-throughput task queues, caching task results, real-time event streams, leaderboards, session management.
    *   **Configuration**:
        ```yaml
        # Example for task queue using Redis backend
        task_queue:
          type: redis
          host: localhost
          port: 6379
          db: 0
        ```

*   **NATS**:
    *   **Description**: A high-performance, open-source messaging system for cloud native applications, IoT, and microservices.
    *   **Use Cases**: Distributed task queuing, real-time eventing, inter-service communication in microservice architectures.
    *   **Configuration**:
        ```yaml
        # Example for task queue using NATS backend
        task_queue:
          type: nats
          servers:
            - nats://localhost:4222
            - nats://nats.example.com:4222
        ```

*   **Memory**:
    *   **Description**: An in-memory backend, meaning data is not persisted beyond the current application session.
    *   **Use Cases**: Testing, development, short-lived tasks where results/events do not need to be stored permanently.
    *   **Configuration**:
        ```yaml
        # Example for any component using memory backend
        result_storage:
          type: memory
        ```

## Backend Configuration in OmniQ

When initializing OmniQ, you can specify the desired backend for each component:

```python
from omniq import OmniQ
from omniq.config import OmniQConfig

# Configure OmniQ to use different backends for each component
config = OmniQConfig(
    task_queue_type="redis",
    result_storage_type="sqlite",
    event_storage_type="postgresql",
    # Backend-specific configurations
    redis_host="localhost",
    redis_port=6379,
    sqlite_database_path="omniq_results.db",
    postgresql_dsn="postgresql://user:password@localhost:5432/omniq_events"
)

omniq = OmniQ(config=config)
```

This modularity is a core strength of OmniQ, providing the flexibility to adapt to diverse operational requirements and infrastructure setups.