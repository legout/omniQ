import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium", auto_download=["ipynb"])


@app.cell
def _():
    from omniq.workers import (
        ThreadPoolWorker,
        AsyncWorker,
        AsyncGeventWorker,
        AsyncProcessWorker,
        GeventPoolWorker,
        ProcessPoolWorker,
    )

    import datetime as dt
    from omniq.queue import (
        FileQueue,
        SQLiteQueue,
        NATSQueue,
        RedisQueue,
        PostgresQueue,
    )
    from omniq.results import (
        FileResultStorage,
        SQLiteResultStorage,
        NATSResultStorage,
        RedisResultStorage,
        PostgresResultStorage,
    )
    from omniq.events import (
        PostgresEventStorage,
        FileEventStorage,
        SQLiteEventStorage,
    )
    return FileQueue, SQLiteResultStorage, ThreadPoolWorker


@app.cell
def _(FileQueue, SQLiteResultStorage):
    # Create components individually
    queue = FileQueue(
        base_dir="some/path",
        #queues=["low", "medium", "high"]
    )

    result_store = SQLiteResultStorage(
        db_path="some/path/sqlite.db"
    )

    print("Created individual components:")
    print(f"- Task Queue: {type(queue).__name__}")
    print(f"- Result Store: {type(result_store).__name__}")
    return queue, result_store


@app.cell
def _(ThreadPoolWorker, queue, result_store):
    # Create worker with reference to queue and result store
    worker = ThreadPoolWorker(
        queue=queue,
        result_storage=result_store,
        event_storage=None,
        max_concurrent_tasks=20
    )

    return (worker,)


@app.cell
def _(worker):
    worker.start()
    return


@app.cell
def _():
    # Define a task
    def simple_task(name):
        print(f"Hello {name}")
        return name

    print("Defined simple_task function")
    return (simple_task,)


@app.cell
def _(queue, simple_task):
    # Enqueue a task
    task_id = queue.enqueue(
        func=simple_task,
        func_args=dict(name="Tom"),
        queue_name="low"
    )
    print(f"Enqueued task with ID: {task_id}")

    return


@app.cell
def _(worker):
    help(worker.start)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
