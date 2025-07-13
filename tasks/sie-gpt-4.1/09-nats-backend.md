<!-- @/tasks/09-nats-backend.md -->
# Subtask 2.4: NATS.io Backend

**Objective:**  
Implement a high-performance NATS.io backend for streaming distributed task and result messaging in OmniQ.

**Requirements:**  
- Use `nats-py` for client connections (async-first).
- Implement named queues via subject prefixes; support queue groups for exclusive task consumption.
- Provide result and event streaming (reliable receive, replay).
- Implement task locking as needed using NATS queue semantics.
- Support TTL and expired task cleanup.
- Both async and sync interfaces.
- Test using local/dev NATS servers.

**Context from Project Plan:**  
- Review “Key Design Decisions: Task Locking” for NATS details.

**Dependencies:**  
- Must comply with declared task/result/event interfaces.

**Deliverables:**  
- NATS backend implementation in `src/omniq/storage/nats.py` with full tests.