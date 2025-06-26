import asyncio
import logging
import os
import signal
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional

from omniq.core import OmniQ
from omniq.workers.base import BaseWorker
from omniq.workers.executor import execute_task

logger = logging.getLogger(__name__)

# Global flag to signal shutdown in the child process
_shutdown_in_process = False


def _handle_shutdown_signal(sig, frame):
    """Signal handler for child processes."""
    global _shutdown_in_process
    if not _shutdown_in_process:
        _shutdown_in_process = True
        logging.getLogger(__name__).info(
            f"Process {os.getpid()} received signal {sig}, shutting down gracefully."
        )


def _process_worker_loop(
    task_queue_url: str,
    result_storage_url: str,
    queues: List[str],
    worker_id_prefix: str,
    log_level: str,
):
    """The main loop for a worker running in a separate process."""
    # Configure logging for the new process. `force=True` is important.
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(processName)s - %(levelname)s - %(message)s",
        force=True,
    )

    # Ignore SIGINT in child (parent handles it). Handle SIGTERM for graceful shutdown.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    omniq = OmniQ(task_queue_url=task_queue_url, result_storage_url=result_storage_url)
    worker_id = f"{worker_id_prefix}-{os.getpid()}"
    process_logger = logging.getLogger(__name__)
    process_logger.info(f"Process worker {worker_id} started for queues: {queues}")

    global _shutdown_in_process
    while not _shutdown_in_process:
        try:
            # Use asyncio.run for each async operation in the sync loop
            task = asyncio.run(omniq.task_queue.dequeue(queues, timeout=1))
            if task:
                # `running_in_thread=True` is appropriate as we are not in an async event loop
                asyncio.run(execute_task(omniq, task, worker_id, running_in_thread=True))
            # If no task, the loop continues and checks the shutdown flag
        except Exception as e:
            process_logger.error(f"Error in process worker loop: {e}", exc_info=True)
            # Avoid fast-spinning on persistent errors (e.g., DB connection)
            time.sleep(1)

    process_logger.info(f"Process worker {worker_id} finished.")


class ProcessPoolWorker(BaseWorker):
    """
    A worker that runs tasks in a process pool.
    Ideal for CPU-bound tasks that can be pickled.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor: Optional[ProcessPoolExecutor] = None

    async def run(self) -> None:
        """Starts the process pool and submits worker loops."""
        logger.info(f"Starting {self.worker_id} with {self.concurrency} processes for queues: {self.queues}")
        self.install_signal_handlers()

        # Get the current log level to pass to child processes
        log_level = logging.getLevelName(logging.getLogger().getEffectiveLevel())

        self.executor = ProcessPoolExecutor(max_workers=self.concurrency)
        for _ in range(self.concurrency):
            self.executor.submit(
                _process_worker_loop,
                self.omniq.config.task_queue_url,
                self.omniq.config.result_storage_url,
                self.queues,
                self.worker_id,
                log_level,
            )

        await self._shutdown_event.wait()

    async def shutdown(self, *args, **kwargs) -> None:
        """Shuts down the process pool executor."""
        await super().shutdown(*args, **kwargs)
        if self.executor:
            logger.info(f"ProcessPoolWorker {self.worker_id} shutting down executor...")
            # This sends SIGTERM to child processes, triggering their shutdown handler.
            self.executor.shutdown(wait=True)
        logger.info(f"ProcessPoolWorker {self.worker_id} shutdown complete.")