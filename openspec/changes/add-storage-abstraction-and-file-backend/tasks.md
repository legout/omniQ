## 1. Base Storage Interface
- [ ] 1.1 Define `BaseStorage` in `src/omniq/storage/base.py` with async methods for enqueue, dequeue, mark_running, mark_done, mark_failed, get_result, purge_results, and optional reschedule.
- [ ] 1.2 Ensure the interface uses core task and result models from `omniq.models`.
- [ ] 1.3 Document ordering and visibility expectations for dequeue and result retrieval.

## 2. File Storage Backend
- [ ] 2.1 Implement `FileStorage` in `src/omniq/storage/file.py` using a directory layout for `queue/` and `results/`.
- [ ] 2.2 Use atomic file operations (e.g., `os.rename`) or equivalent to ensure each dequeued task is claimed at most once.
- [ ] 2.3 Integrate serialization hooks so that tasks and results are encoded/decoded via the active serializer.

## 3. Tests and Validation
- [ ] 3.1 Add tests covering enqueue/dequeue, mark_* operations, and result retrieval for `FileStorage`.
- [ ] 3.2 Add tests for basic scheduling behavior (`eta`-based visibility) using `FileStorage`.

