import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from croniter import croniter

from omniq import OmniQ
from omniq.models import Schedule, Task
from omniq.scheduler import Scheduler
from tests.helpers import sync_add


# --- Fixtures ---


@pytest.fixture
def scheduler(omniq_instance):
    """Provides a Scheduler instance with a short check interval."""
    return Scheduler(omniq_instance, check_interval=0.1)


# --- Tests ---


@pytest.mark.asyncio
async def test_scheduler_interval_scheduling(omniq_instance: OmniQ, scheduler: Scheduler):
    """Verify that an interval-based schedule enqueues its task."""
    # Mock the enqueue method to count calls
    omniq_instance.enqueue = MagicMock(wraps=omniq_instance.enqueue)

    # Create an interval schedule
    task_to_schedule = Task(func=sync_add, args=(1, 1), queue="scheduled_tasks")
    schedule = Schedule(task=task_to_schedule, interval=0.2)  # Every 0.2 seconds
    await omniq_instance.add_schedule(schedule)

    run_task = asyncio.create_task(scheduler.run())

    # Wait for a bit to allow the scheduler to run at least once
    await asyncio.sleep(0.3)

    # Check that the task was enqueued
    assert omniq_instance.enqueue.call_count >= 1
    omniq_instance.enqueue.assert_called_with(
        task_to_schedule.func,
        1,
        1,
        queue="scheduled_tasks",
    )

    # Verify schedule state update
    updated_schedule = await omniq_instance.get_schedule(schedule.id)
    assert updated_schedule is not None
    assert updated_schedule.last_run_at is not None
    assert updated_schedule.next_run_at is not None
    assert updated_schedule.next_run_at > updated_schedule.last_run_at

    await scheduler.shutdown()
    await run_task


@pytest.mark.asyncio
async def test_scheduler_cron_scheduling(omniq_instance: OmniQ, scheduler: Scheduler):
    """Verify that a cron-based schedule enqueues its task at the correct time."""
    omniq_instance.enqueue = MagicMock(wraps=omniq_instance.enqueue)

    # Schedule to run every second (e.g., "* * * * * *")
    # Using a specific minute/second to ensure it triggers
    now = datetime.now()
    # Set cron to trigger at the next whole second + a small buffer
    next_second = (now + timedelta(seconds=1)).replace(microsecond=0)
    cron_expression = f"{next_second.second} {next_second.minute} {next_second.hour} * * *"

    task_to_schedule = Task(func=sync_add, args=(2, 2), queue="cron_tasks")
    schedule = Schedule(task=task_to_schedule, cron=cron_expression)
    await omniq_instance.add_schedule(schedule)

    run_task = asyncio.create_task(scheduler.run())

    # Wait until after the expected cron trigger time
    wait_time = (next_second - now).total_seconds() + 0.1 + scheduler.check_interval
    await asyncio.sleep(wait_time)

    assert omniq_instance.enqueue.call_count >= 1
    omniq_instance.enqueue.assert_called_with(
        task_to_schedule.func,
        2,
        2,
        queue="cron_tasks",
    )

    # Verify schedule state update
    updated_schedule = await omniq_instance.get_schedule(schedule.id)
    assert updated_schedule is not None
    assert updated_schedule.last_run_at is not None
    assert updated_schedule.next_run_at is not None
    assert updated_schedule.next_run_at > updated_schedule.last_run_at

    await scheduler.shutdown()
    await run_task


@pytest.mark.asyncio
async def test_scheduler_paused_schedule(omniq_instance: OmniQ, scheduler: Scheduler):
    """Verify that a paused schedule does not enqueue its task."""
    omniq_instance.enqueue = MagicMock(wraps=omniq_instance.enqueue)

    task_to_schedule = Task(func=sync_add, args=(3, 3), queue="paused_tasks")
    schedule = Schedule(task=task_to_schedule, interval=0.1, is_paused=True)
    await omniq_instance.add_schedule(schedule)

    run_task = asyncio.create_task(scheduler.run())
    await asyncio.sleep(0.3)  # Give it time to check

    assert omniq_instance.enqueue.call_count == 0

    await scheduler.shutdown()
    await run_task


@pytest.mark.asyncio
async def test_scheduler_multiple_schedules(omniq_instance: OmniQ, scheduler: Scheduler):
    """Verify that the scheduler handles multiple schedules concurrently."""
    omniq_instance.enqueue = MagicMock(wraps=omniq_instance.enqueue)

    task1 = Task(func=sync_add, args=(10, 10), queue="multi_q1")
    schedule1 = Schedule(task=task1, interval=0.2)
    await omniq_instance.add_schedule(schedule1)

    # Cron for next second
    now = datetime.now()
    next_second = (now + timedelta(seconds=1)).replace(microsecond=0)
    cron_expression = f"{next_second.second} {next_second.minute} {next_second.hour} * * *"
    task2 = Task(func=sync_add, args=(20, 20), queue="multi_q2")
    schedule2 = Schedule(task=task2, cron=cron_expression)
    await omniq_instance.add_schedule(schedule2)

    run_task = asyncio.create_task(scheduler.run())

    # Wait long enough for both schedules to potentially trigger
    wait_time = (next_second - now).total_seconds() + 0.1 + scheduler.check_interval
    await asyncio.sleep(max(0.3, wait_time))

    assert omniq_instance.enqueue.call_count >= 2
    omniq_instance.enqueue.assert_any_call(task1.func, 10, 10, queue="multi_q1")
    omniq_instance.enqueue.assert_any_call(task2.func, 20, 20, queue="multi_q2")

    await scheduler.shutdown()
    await run_task


@pytest.mark.asyncio
async def test_scheduler_graceful_shutdown(omniq_instance: OmniQ, scheduler: Scheduler):
    """Verify that the scheduler shuts down gracefully."""
    run_task = asyncio.create_task(scheduler.run())
    await asyncio.sleep(0.1)  # Allow scheduler to start its loop

    await scheduler.shutdown()
    await run_task  # Wait for the run task to complete

    # If we reach here without exceptions, shutdown was graceful.
    # We can also check internal state if necessary, but the lack of hanging
    # or errors is a good indicator.
    assert scheduler._shutdown_event.is_set()