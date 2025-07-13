<!-- @/tasks/03-scheduling-and-dependency-engine.md -->
# Subtask 1.3: Core Scheduling and Dependency Engine

**Objective:**  
Implement the scheduling engine and dependency graph management for tasks.

**Requirements:**  
- Produce async (with sync wrappers) schedulers that handle immediate, interval, and cron-based schedules (using `croniter` and `python-dateutil`).
- Support pausing and resuming of scheduled tasks.
- Implement a task dependency graph to enforce dependency-based task execution.
- Ensure all metadata/state changes generate appropriate events via the event system.

**Context from Project Plan:**  
- Refer to “Task Queue Engine” and “Task Models” for required features.

**Deliverables:**  
- Scheduler and dependency resolver modules under `src/omniq/queue/`.