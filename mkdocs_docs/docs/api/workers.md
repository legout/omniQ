# Workers

This section will describe the different worker types and their usage.

OmniQ provides several worker types to execute tasks:

- **Async Worker**: Native async execution.
  - `omniq.workers.async.AsyncWorker`
- **Thread Worker**: Thread pool execution.
  - `omniq.workers.thread.ThreadWorker`
- **Process Worker**: Process pool execution.
  - `omniq.workers.process.ProcessWorker`
- **Gevent Worker**: Gevent pool execution.
  - `omniq.workers.gevent.GeventWorker`

Key features of workers:
- All worker types can handle both sync and async tasks.
- Async workers run sync tasks in thread pools.
- Thread/process workers run async tasks in event loops.
- Workers can process tasks from multiple queues with priority ordering.