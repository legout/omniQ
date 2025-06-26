import asyncio
import time

# --- Test Task Functions & Classes ---


def sync_add(x, y):
    """A simple synchronous task."""
    return x + y


async def async_add(x, y):
    """A simple asynchronous task."""
    await asyncio.sleep(0.01)
    return x + y


def sync_fail():
    """A synchronous task that always fails."""
    raise ValueError("Sync task failed")


async def async_sleep(duration):
    """An async task that sleeps without blocking."""
    await asyncio.sleep(duration)
    return duration


def sync_sleep(duration):
    """A sync task that sleeps, blocking its thread."""
    time.sleep(duration)
    return duration


def cpu_intensive_task(count_to: int):
    """A task that is purely CPU-bound. Must be a top-level function to be pickled."""
    c = 0
    for i in range(count_to):
        c += 1
    return c


class StatefulFailer:
    """A class to test retries. dill can serialize instances of it."""

    def __init__(self):
        self.attempts = 0

    def fail_once(self):
        self.attempts += 1
        if self.attempts <= 1:
            raise ValueError("Failing on purpose")
        return "Success on attempt 2"