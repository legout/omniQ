# Working with Multiple Queues Examples

This directory contains examples demonstrating how to work with multiple named queues in the OmniQ library, including priority-based processing and queue management.

## Files

- **`multiple_queues.py`**: Demonstrates working with multiple named queues and priority-based task processing
- **`multiple_queues.ipynb`**: Jupyter notebook containing interactive examples of multiple queue usage with detailed explanations

## Overview

OmniQ supports multiple named queues within a single task queue instance, allowing you to:

1. **Organize Tasks by Priority**: Use different queues for different priority levels (high, medium, low)
2. **Priority-Based Processing**: Workers process queues in priority order, handling high-priority tasks first
3. **Queue-Specific Configuration**: Configure different settings for different queues
4. **Flexible Queue Management**: Add, remove, and manage queues dynamically
5. **Load Balancing**: Distribute tasks across multiple queues based on workload

## Multiple Queue Architecture

All OmniQ task queue implementations support multiple named queues:

- **File Queue**: Uses directory structure with separate directories for each queue
- **SQLite/PostgreSQL Queue**: Uses queue column with priority ordering in SQL queries
- **Redis Queue**: Uses queue prefixes for different named queues
- **NATS Queue**: Uses subject prefixes for queue separation
- **Memory Queue**: Uses in-memory separation with priority ordering

## Priority-Based Processing

Workers process queues in the order they are specified, creating a natural priority system:

```python
# Queues are processed in this order: high -> medium -> low
queues = ["high", "medium", "low"]
worker = ThreadPoolWorker(queue=queue, max_workers=10)
```

The worker will:
1. Check the "high" queue first and process all available tasks
2. Move to "medium" queue only when "high" queue is empty
3. Process "low" queue tasks only when both "high" and "medium" are empty

## Benefits

- **Priority Management**: Ensure critical tasks are processed before less important ones
- **Resource Allocation**: Allocate more workers to high-priority queues
- **Task Organization**: Group related tasks in specific queues
- **Performance Optimization**: Optimize processing based on task characteristics
- **Monitoring**: Track queue-specific metrics and performance

## Use Cases

### Priority-Based Task Processing
- **High Priority**: Critical system tasks, user-facing operations
- **Medium Priority**: Background processing, data synchronization
- **Low Priority**: Cleanup tasks, analytics, reporting

### Department-Based Queues
- **Sales**: Customer orders, lead processing
- **Marketing**: Email campaigns, analytics
- **Support**: Ticket processing, notifications

### Processing-Type Queues
- **Fast**: Quick operations that complete in seconds
- **Slow**: Long-running operations that take minutes or hours
- **Batch**: Bulk operations that process multiple items

## Queue Management Best Practices

1. **Define Clear Priorities**: Establish clear criteria for which tasks go in which queues
2. **Monitor Queue Lengths**: Track queue sizes to identify bottlenecks
3. **Balance Workers**: Allocate appropriate worker resources to each priority level
4. **Avoid Queue Starvation**: Ensure low-priority queues eventually get processed
5. **Use Descriptive Names**: Choose queue names that clearly indicate their purpose

## When to Use Multiple Queues

Use multiple queues when you need:

- **Priority-based task processing** with different urgency levels
- **Resource allocation** based on task importance
- **Task organization** by type, department, or processing requirements
- **Performance optimization** with different processing strategies
- **Monitoring and metrics** at the queue level

For simpler use cases with single queue processing, consider the basic usage examples in `../01_basic_usage/`.

## Supported Queue Types

All OmniQ queue implementations support multiple named queues:

- **FileTaskQueue**: Directory-based queue separation
- **MemoryTaskQueue**: In-memory queue separation
- **SQLiteTaskQueue**: Database column-based queue management
- **PostgresTaskQueue**: Database column-based queue management with advanced features
- **RedisTaskQueue**: Redis key prefix-based queue separation
- **NATSTaskQueue**: NATS subject-based queue separation

Each implementation optimizes multiple queue support based on the underlying storage technology while maintaining a consistent API across all queue types.