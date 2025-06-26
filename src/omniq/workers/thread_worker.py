import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from omniq.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class ThreadPoolWorker(BaseWorker):
    """
    A worker that runs tasks in a thread pool.
    Ideal for CPU-bound or blocking I/O synchronous tasks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor: Optional[ThreadPoolExecutor] = None

    def _worker_loop(self):
        """The core loop for a single worker thread."""
        # This loop runs in a separate thread.
        while not self._shutdown_event.is_set():
            try:
                # We run the async dequeue method in its own event loop in this thread.
                # A timeout of 1s makes this a polling operation.
                task = asyncio.run(self.omniq.task_queue.dequeue(self.queues, timeout=1))

                if task:
                    # _execute_task is async, so we run it in a new event loop.
                    # We pass running_in_thread=True for optimization.
                    asyncio.run(self._execute_task(task, running_in_thread=True))
                else:
                    # No task, loop continues to check for shutdown.
                    continue
            except Exception as e:
                # Catch exceptions to prevent the worker thread from dying.
                logger.error(f"Error in thread worker loop: {e}", exc_info=True)
                # Wait a bit before retrying to avoid fast-spinning on persistent errors.
                self._shutdown_event.wait(1)

    async def run(self) -> None:
        """Starts the thread pool and submits worker loops."""
        logger.info(f"Starting {self.worker_id} with {self.concurrency} threads for queues: {self.queues}")
        self.install_signal_handlers()

        self.executor = ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix=self.worker_id)
        for _ in range(self.concurrency):
            self.executor.submit(self._worker_loop)

        await self._shutdown_event.wait()

    async def shutdown(self, *args, **kwargs) -> None:
        """Shuts down the thread pool executor."""
        await super().shutdown(*args, **kwargs)
        if self.executor:
            logger.info(f"ThreadPoolWorker {self.worker_id} waiting for threads to finish...")
            self.executor.shutdown(wait=True)
        logger.info(f"ThreadPoolWorker {self.worker_id} shutdown complete.")