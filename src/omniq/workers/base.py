import asyncio
import logging
import signal
import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from omniq.core import OmniQ
from omniq.models import Task, TaskResult
from omniq.workers.executor import execute_task

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Abstract base class for all workers."""

    def __init__(
        self,
        omniq_instance: OmniQ,
        queues: Optional[List[str]] = None,
        concurrency: int = 10,
        worker_id: Optional[str] = None,
    ):
        self.omniq = omniq_instance
        self.queues = queues or ["default"]
        self.concurrency = concurrency
        self.worker_id = worker_id or f"{self.__class__.__name__}-{uuid.uuid4()}"
        self._shutdown_event = asyncio.Event()

    @abstractmethod
    async def run(self) -> None:
        """Starts the worker's main loop."""
        raise NotImplementedError

    async def shutdown(self, sig: Optional[signal.Signals] = None) -> None:
        """Initiates a graceful shutdown by setting the shutdown event."""
        if self._shutdown_event.is_set():
            return
        if sig:
            logger.info(f"Received signal {sig.name}. Worker {self.worker_id} shutting down...")
        else:
            logger.info(f"Worker {self.worker_id} shutting down...")
        self._shutdown_event.set()

    def install_signal_handlers(self) -> None:
        """Installs signal handlers for graceful shutdown."""
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.shutdown(s)))
        except (RuntimeError, NotImplementedError):
            logger.warning("Could not install signal handlers. Running in a non-standard environment?")

    async def _execute_task(self, task: Task, running_in_thread: bool = False) -> None:
        """Deserializes and executes a task, handling results and errors."""
        await execute_task(self.omniq, task, self.worker_id, running_in_thread)