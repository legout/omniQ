# Component-Based Usage Examples

This directory contains examples demonstrating the component-based approach to using the OmniQ library, where each component (Queue, Result Store, Worker) is instantiated and used separately.

## Files

- **`component_usage.py`**: Demonstrates component-based usage with individual component instantiation
- **`component_usage.ipynb`**: Jupyter notebook containing the same example with detailed explanations about decoupling components

## Overview

The component-based approach provides maximum flexibility by allowing you to:

1. **Decouple Components**: Create and configure each component (task queue, result storage, event storage, worker) independently
2. **Mix and Match Backends**: Use different storage backends for different components (e.g., file-based queue with SQLite results)
3. **Fine-Grained Control**: Configure each component with specific settings optimized for your use case
4. **Modular Architecture**: Replace or upgrade individual components without affecting others
5. **Direct Component Access**: Work directly with component APIs for advanced use cases

## Component Architecture

In the component-based approach, you work with these main components:

- **Task Queue**: Stores and manages task execution queue (`FileTaskQueue`, `SQLiteTaskQueue`, etc.)
- **Result Storage**: Stores and retrieves task execution results (`SQLiteResultStorage`, `FileResultStorage`, etc.)
- **Event Storage**: Logs task lifecycle events for monitoring (`PostgresEventStorage`, `SQLiteEventStorage`, etc.)
- **Worker**: Executes tasks from the queue (`ThreadPoolWorker`, `AsyncWorker`, etc.)

## Benefits

- **Flexibility**: Choose the best backend for each component based on your specific requirements
- **Scalability**: Scale components independently (e.g., multiple workers with shared storage)
- **Testing**: Mock individual components for unit testing
- **Migration**: Migrate components one at a time without system-wide changes
- **Performance**: Optimize each component's configuration for its specific workload

## When to Use Component-Based Approach

Use this approach when you need:
- Different storage backends for different components
- Fine-grained control over component configuration
- To integrate OmniQ components into existing systems
- Maximum flexibility and customization
- To build custom orchestration logic around OmniQ components

For simpler use cases, consider the basic usage examples in `../01_basic_usage/` or backend-based configuration.