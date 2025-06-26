import asyncio
import logging
import signal
import time
from typing import Optional

from croniter import croniter

from omniq.core import OmniQ
from omniq.models import Schedule

logger = logging.getLogger(__name__)


class Scheduler:
    """
    The OmniQ Scheduler. Responsible for periodically checking scheduled tasks
    and enqueuing them when due.
    """

    def __init__(
        self,
        omniq_instance: OmniQ,
        check_interval: float = 5.0,  # How often to check for due schedules (seconds)
        scheduler_id: Optional[str] = None,
    ):
        self.omniq = omniq_instance
        self.check_interval = check_interval
        self.scheduler_id = scheduler_id or f"Scheduler-{time.time_ns()}"
        self._shutdown_event = asyncio.Event()

    def install_signal_handlers(self) -> None:
        """Installs signal handlers for graceful shutdown."""
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(self.shutdown(s)))
        except (RuntimeError, NotImplementedError):
            logger.warning("Could not install signal handlers. Running in a non-standard environment?")

    async def _calculate_next_run_time(self, schedule: Schedule) -> Optional[float]:
        """Calculates the next run time for a schedule."""
        now = time.time()
        if schedule.cron:
            # croniter expects datetime objects
            base_time = schedule.last_run_at if schedule.last_run_at else now
            itr = croniter(schedule.cron, start_time=base_time)
            return itr.get_next(float)
        elif schedule.interval:
            if schedule.last_run_at:
                return schedule.last_run_at + schedule.interval
            return now + schedule.interval  # Run immediately if no last_run_at
        return None

    async def run(self) -> None:
        """Starts the scheduler's main loop."""
        logger.info(f"Scheduler {self.scheduler_id} starting...")
        self.install_signal_handlers()

        while not self._shutdown_event.is_set():
            try:
                schedules = await self.omniq.list_schedules()
                now = time.time()

                for schedule in schedules:
                    if schedule.is_paused:
                        continue

                    # Calculate next run time if not already set or if it's in the past
                    if schedule.next_run_at is None or schedule.next_run_at <= now:
                        schedule.next_run_at = await self._calculate_next_run_time(schedule)
                        # Update the schedule in storage immediately after calculating next_run_at
                        await self.omniq.add_schedule(schedule)

                    if schedule.next_run_at and schedule.next_run_at <= now:
                        logger.info(f"Enqueuing scheduled task: {schedule.id}")
                        # Enqueue the task associated with the schedule
                        # The task object within the schedule is already a Task model
                        await self.omniq.enqueue(
                            func=schedule.task.func,
                            *schedule.task.args,
                            queue=schedule.task.queue,
                            **schedule.task.kwargs,
                        )
                        schedule.last_run_at = now
                        schedule.next_run_at = await self._calculate_next_run_time(schedule)
                        await self.omniq.add_schedule(schedule)  # Update schedule in storage

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval)

        logger.info(f"Scheduler {self.scheduler_id} shutting down.")

    async def shutdown(self, sig: Optional[signal.Signals] = None) -> None:
        """Initiates a graceful shutdown."""
        if sig:
            logger.info(f"Received signal {sig.name}. Scheduler {self.scheduler_id} shutting down...")
        self._shutdown_event.set()