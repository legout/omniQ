<!-- @/tasks/04-worker-pool-and-execution.md -->
# Subtask 1.4: Core Worker Pool and Execution Logic

**Objective:**  
Develop a modular worker pool and unified task execution subsystem that works across backend storage types and both sync/async tasks.

**Requirements:**  
- Provide AsyncWorker, ThreadPoolWorker, ProcessPoolWorker, and GeventWorker (core async, with sync wrappers).
- Support for max_workers and runtime configuration.
- Implement logic to run async/sync Python callables, respecting task TTL and timeouts.
- Handle callbacks, result storage, and event logging for task state transitions.

**Context from Project Plan:**  
- See “Worker Layer" and “Event System” for relevant requirements.

**Deliverables:**  
- Worker implementations and base interfaces under `src/omniq/workers/`.