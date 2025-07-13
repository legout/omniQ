<!-- @/tasks/01-core-interfaces-and-models.md -->
# Subtask 1.1: Define Core Interfaces and Models

**Objective:**  
Design and implement the core data models and interfaces for OmniQ, ensuring extensibility to support an arbitrary number of storage, result, and event backends.  

**Requirements:**  
- Define domain models: `Task`, `TaskResult`, `Schedule`, `TaskEvent`, and `Settings`, using `msgspec.Struct` for type-safety and serialization.  
- Specify abstract base classes/interfaces (`ABC`s) for all critical components:  
  - Task Queue (`BaseTaskQueue`)
  - Result Storage (`BaseResultStorage`)
  - Event Storage (`BaseEventStorage`)
  - Worker (`BaseWorker`)
- Each interface should offer both sync and async methods, using an "Async First, Sync Wrapped" pattern.  
- Models must include unique identifiers, TTL support, status enums, dependency tracking, error/result states, run/schedule metadata, and serialization hints.
- Include hashable/equatable support for tasks where needed (dependency graph support).
- Settings must be overridable via environment variables with the `OMNIQ_` prefix.

**Context from Project Plan:**  
- Refer to the “Core Design Principles” and “Module Architecture” for guidance on how to keep separation of concerns and maintain interface-driven, extensible architecture.
- Ensure “Component Separation,” “Backend Abstraction,” and “Async First, Sync Wrapped” patterns are central in all interface definitions.

**Deliverables:**  
- Full model definitions in `src/omniq/models/`  
- Abstract base interface definitions in their respective modules (`src/omniq/queue/base.py`, `src/omniq/storage/base.py`, etc.).
- Brief inline documentation for each model/interface.