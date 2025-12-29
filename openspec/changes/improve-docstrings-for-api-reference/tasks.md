## 1. Critical Missing Docstrings
- [x] Add docstring to `Schedule` TypedDict in `models.py` with full field documentation
- [x] Add docstring to `Task` TypedDict in `models.py` with full field documentation
- [x] Add docstring to `TaskResult` TypedDict in `models.py` with full field documentation
- [x] Add docstring to `BackendType` enum in `config.py` with backend tradeoffs
- [x] Add complete docstring to `Settings.__init__` in `config.py` with Args, Raises sections

## 2. Add Examples to Public Façade APIs
- [x] Add usage example to `AsyncOmniQ.enqueue()` in `core.py`
- [x] Add usage example to `AsyncOmniQ.get_result()` in `core.py`
- [x] Add usage example to `AsyncOmniQ.worker()` in `core.py`
- [x] Add usage example to `Settings.from_env()` in `config.py`

## 3. Add Examples to Power-User APIs
- [x] Add usage example to `AsyncTaskQueue.enqueue()` in `queue.py`
- [x] Add usage example to `AsyncTaskQueue.dequeue()` in `queue.py`
- [x] Add usage example to `AsyncTaskQueue.complete_task()` in `queue.py`
- [x] Add usage example to `AsyncTaskQueue.fail_task()` in `queue.py`
- [x] Add usage example to `AsyncWorkerPool` initialization and usage in `worker.py`

## 4. Improve Storage Backend Docstrings
- [x] Add Args/Raises/Returns sections to `FileStorage.enqueue()` in `storage/file.py`
- [x] Add Args/Raises/Returns sections to `FileStorage.dequeue()` in `storage/file.py`
- [x] Add Args/Raises/Returns sections to `SQLiteStorage.enqueue()` in `storage/sqlite.py`
- [x] Add Args/Raises/Returns sections to `SQLiteStorage.dequeue()` in `storage/sqlite.py`
- [x] Add brief class docstring to `Serializer` Protocol in `serialization.py`

## 5. Improve Logging Module
- [x] Add Args sections to `log_task_enqueued()` in `logging.py`
- [x] Add Args sections to `log_task_started()` in `logging.py`
- [x] Add Args sections to `log_task_completed()` in `logging.py`
- [x] Add Args sections to `log_task_failed()` in `logging.py`

## 6. Validation
- [x] Run `mkdocs build` to confirm mkdocstrings generates documentation
- [x] Verify all examples in docstrings are correct and runnable
- [x] Confirm type hints match docstring descriptions
