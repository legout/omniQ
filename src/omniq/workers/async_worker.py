import asyncio
import logging
from typing import Set

from omniq.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class AsyncWorker(BaseWorker):
    """
    A worker that uses asyncio to run tasks concurrently.
    Ideal for I/O-bound tasks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This will hold the asyncio.Task objects for the worker loops
        self._worker_tasks: Set[asyncio.Task] = set()

    async def _worker_loop(self):
        """The core loop for a single concurrent worker task."""
        task_being_processed = None
        while not self._shutdown_event.is_set():
            try:
                # Use a short timeout to allow the shutdown event to be checked periodically
                task_being_processed = await self.omniq.task_queue.dequeue(
                    self.queues, timeout=1
                )
                if task_being_processed:
                    # We are in an async worker, so running_in_thread is False
                    await self._execute_task(task_being_processed, running_in_thread=False)
                    task_being_processed = None  # Clear after successful processing
                else:
                    # No task, loop continues to check for shutdown
                    continue
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled.")
                if task_being_processed:
                    logger.info(f"Re-queueing task {task_being_processed.id} due to shutdown.")
                    await self.omniq.task_queue.nack(task_being_processed, requeue=True)
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                if task_being_processed:
                    # This is a fallback. _execute_task should handle its own errors.
                    await self.omniq.task_queue.nack(task_being_processed, requeue=True)
                await asyncio.sleep(1)  # Prevent fast-spinning loop on persistent errors

    async def run(self) -> None:
        """Starts the worker and its concurrent task loops."""
        logger.info(f"Starting {self.worker_id} with concurrency {self.concurrency} for queues: {self.queues}")
        self.install_signal_handlers()

        for _ in range(self.concurrency):
            task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.add(task)
            task.add_done_callback(self._worker_tasks.discard)

        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks)

    async def shutdown(self, *args, **kwargs) -> None:
        """Shuts down the worker by cancelling all running tasks."""
        await super().shutdown(*args, **kwargs)  # Sets the event
        for task in list(self._worker_tasks):
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        logger.info(f"AsyncWorker {self.worker_id} shutdown complete.")