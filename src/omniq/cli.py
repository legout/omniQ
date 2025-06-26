import asyncio
import importlib.metadata
import importlib
import json
import logging
from enum import Enum
from typing import Callable, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from datetime import datetime, timezone

from omniq.core import OmniQ
from omniq.dashboard.app import create_app
from omniq.models import Schedule, Task
from omniq.scheduler import Scheduler
from omniq.workers import AsyncWorker, ProcessPoolWorker, ThreadPoolWorker, BaseWorker

app = typer.Typer(
    name="omniq",
    help="A Flexible Task Queue Library for Python.",
    add_completion=False,
)

schedule_app = typer.Typer(
    name="schedule",
    help="Manage task schedules.",
    no_args_is_help=True,
)
app.add_typer(schedule_app)

class WorkerType(str, Enum):
    """Enum for the available worker types."""

    ASYNC = "async"
    THREAD = "thread"
    PROCESS = "process"


def version_callback(value: bool):
    """Prints the version of the package and exits."""
    if value:
        try:
            version = importlib.metadata.version("omniq")
        except importlib.metadata.PackageNotFoundError:
            version = "0.1.0 (local development)"  # Fallback
        typer.echo(f"OmniQ CLI Version: {version}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit.",
    )
):
    """
    OmniQ command-line interface for managing workers.
    """
    pass


def _start_worker(
    worker_type: WorkerType,
    queues: Optional[List[str]],
    concurrency: int,
    task_queue_url: Optional[str],
    result_storage_url: Optional[str],
    log_level: str,
):
    """The actual logic to configure and start a worker process."""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("omniq.cli")

    actual_queues = queues if queues else ["default"]

    logger.info("Initializing OmniQ worker...")
    logger.info(f"  Worker Type: {worker_type.value}")
    logger.info(f"  Concurrency: {concurrency}")
    logger.info(f"  Queues: {', '.join(actual_queues)}")

    try:
        omniq_instance = OmniQ(
            task_queue_url=task_queue_url, result_storage_url=result_storage_url
        )

        worker_map = {
            WorkerType.ASYNC: AsyncWorker,
            WorkerType.THREAD: ThreadPoolWorker,
            WorkerType.PROCESS: ProcessPoolWorker,
        }
        worker_cls = worker_map[worker_type]
        worker = worker_cls(omniq_instance, queues=actual_queues, concurrency=concurrency)
        asyncio.run(worker.run())
    except Exception as e:
        # This will be logged in the child process if using reload
        logging.getLogger("omniq.cli").error(f"Failed to start worker: {e}", exc_info=True)
        # We don't raise typer.Exit here as it might not behave as expected in a child process
        # The process will exit naturally after the exception.


@app.command(name="run-worker")
def run_worker(
    worker_type: WorkerType = typer.Argument(
        WorkerType.ASYNC,
        help="The type of worker to run.",
        case_sensitive=False,
    ),
    queues: Optional[List[str]] = typer.Option(
        None,
        "--queue",
        "-q",
        help="Queue to consume from. Can be specified multiple times. Defaults to 'default'.",
    ),
    concurrency: int = typer.Option(
        10, "--concurrency", "-c", help="Number of concurrent tasks or threads."
    ),
    task_queue_url: Optional[str] = typer.Option(
        None,
        "--task-queue-url",
        help="URL for the task queue backend (overrides OMNIQ_TASK_QUEUE_URL).",
    ),
    result_storage_url: Optional[str] = typer.Option(
        None,
        "--result-storage-url",
        help="URL for the result storage backend (overrides OMNIQ_RESULT_STORAGE_URL).",
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level (e.g., DEBUG, INFO, WARNING)."
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reloading on code changes for development.",
    ),
):
    """
    Start an OmniQ worker to process tasks.
    """
    if reload:
        try:
            from watchfiles import run_process
        except ImportError:
            typer.echo("Error: 'watchfiles' is not installed. Please run 'pip install \"omniq[reload]\"'.")
            raise typer.Exit(code=1)

        console = Console()
        console.print("Starting worker with [bold green]auto-reload[/] enabled...")
        # watchfiles will run the target in a new process and restart it on file changes.
        run_process(
            ".",  # Watch the current directory
            target=_start_worker,
            kwargs=dict(
                worker_type=worker_type,
                queues=queues,
                concurrency=concurrency,
                task_queue_url=task_queue_url,
                result_storage_url=result_storage_url,
                log_level=log_level,
            ),
        )
    else:
        # Start the worker directly without the reloader
        _start_worker(worker_type, queues, concurrency, task_queue_url, result_storage_url, log_level)


def _import_task_func(func_str: str) -> Callable:
    """Imports a function from a string like 'my.module:my_func'."""
    try:
        module_path, func_name = func_str.rsplit(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ValueError, ImportError, AttributeError) as e:
        raise typer.BadParameter(f"Could not import '{func_str}': {e}")


@schedule_app.command("add")
def add_schedule(
    task_func_str: str = typer.Argument(
        ..., help="Task function to schedule, e.g., 'my_app.tasks:my_task'."
    ),
    cron: Optional[str] = typer.Option(
        None, "--cron", help="Cron expression for the schedule."
    ),
    interval: Optional[float] = typer.Option(
        None, "--interval", help="Interval in seconds for the schedule."
    ),
    args_json: str = typer.Option(
        "[]", "--args", help="JSON array of positional arguments."
    ),
    kwargs_json: str = typer.Option(
        "{}", "--kwargs", help="JSON object of keyword arguments."
    ),
    queue: str = typer.Option("default", "--queue", "-q", help="The queue for the task."),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
):
    """Add a new task schedule."""
    console = Console()
    if not cron and not interval:
        console.print("[bold red]Error:[/] Either --cron or --interval must be provided.")
        raise typer.Exit(code=1)
    if cron and interval:
        console.print("[bold red]Error:[/] Cannot provide both --cron and --interval.")
        raise typer.Exit(code=1)

    try:
        task_func = _import_task_func(task_func_str)
        pos_args = json.loads(args_json)
        kw_args = json.loads(kwargs_json)
    except (json.JSONDecodeError) as e:
        console.print(f"[bold red]Error parsing JSON arguments:[/] {e}")
        raise typer.Exit(code=1)
    except typer.BadParameter as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(code=1)

    task = Task(func=task_func, args=tuple(pos_args), kwargs=kw_args, queue=queue)
    schedule = Schedule(task=task, cron=cron, interval=interval)

    omniq = OmniQ(schedule_storage_url=schedule_storage_url)
    schedule_id = omniq.add_schedule_sync(schedule)
    console.print(f"Successfully added schedule with ID: [bold green]{schedule_id}[/]")


@schedule_app.command("list")
def list_schedules(
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
):
    """List all configured schedules."""
    omniq = OmniQ(schedule_storage_url=schedule_storage_url)
    schedules = omniq.list_schedules_sync()

    console = Console()
    if not schedules:
        console.print("No schedules found.")
        return

    table = Table("ID", "Task", "Schedule", "Queue", "Next Run (UTC)", "Paused")
    for s in schedules:
        next_run_str = datetime.fromtimestamp(s.next_run_at, tz=timezone.utc).isoformat(timespec='seconds') if s.next_run_at else "N/A"
        task_name = f"{s.task.func.__module__}.{s.task.func.__name__}"
        schedule_str = s.cron or f"every {s.interval}s"
        table.add_row(s.id, task_name, schedule_str, s.task.queue, next_run_str, str(s.is_paused))
    console.print(table)


@schedule_app.command("remove")
def remove_schedule(
    schedule_id: str = typer.Argument(..., help="The ID of the schedule to remove."),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
):
    """Remove a task schedule by its ID."""
    console = Console()
    omniq = OmniQ(schedule_storage_url=schedule_storage_url)
    if omniq.get_schedule_sync(schedule_id) is None:
        console.print(f"[bold red]Error:[/] Schedule with ID '{schedule_id}' not found.")
        raise typer.Exit(code=1)

    omniq.remove_schedule_sync(schedule_id)
    console.print(f"Successfully removed schedule with ID: [bold green]{schedule_id}[/]")


def _toggle_schedule_pause(schedule_id: str, schedule_storage_url: Optional[str], pause: bool):
    """Helper function to pause or resume a schedule."""
    console = Console()
    omniq = OmniQ(schedule_storage_url=schedule_storage_url)

    action_past_tense = "paused" if pause else "resumed"
    current_state_str = "paused" if pause else "active"

    schedule = omniq.get_schedule_sync(schedule_id)
    if schedule is None:
        console.print(f"[bold red]Error:[/] Schedule with ID '{schedule_id}' not found.")
        raise typer.Exit(code=1)

    if schedule.is_paused is pause:
        console.print(f"Schedule '{schedule_id}' is already {current_state_str}.")
        raise typer.Exit()

    if pause:
        omniq.pause_schedule_sync(schedule_id)
    else:
        omniq.resume_schedule_sync(schedule_id)

    console.print(f"Successfully {action_past_tense} schedule with ID: [bold green]{schedule_id}[/]")

@schedule_app.command("run")
def run_schedule_now(
    schedule_id: str = typer.Argument(..., help="The ID of the schedule to run immediately."),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
    task_queue_url: Optional[str] = typer.Option(
        None,
        "--task-queue-url",
        help="URL for the task queue backend (overrides OMNIQ_TASK_QUEUE_URL).",
    ),
    result_storage_url: Optional[str] = typer.Option(
        None,
        "--result-storage-url",
        help="URL for the result storage backend (overrides OMNIQ_RESULT_STORAGE_URL).",
    ),
):
    """
    Manually run a scheduled task immediately.
    """
    console = Console()
    omniq = OmniQ(
        schedule_storage_url=schedule_storage_url,
        task_queue_url=task_queue_url,
        result_storage_url=result_storage_url,
    )

    try:
        task_id = omniq.run_schedule_sync(schedule_id)
        if task_id:
            console.print(f"Successfully enqueued task for schedule '{schedule_id}' with Task ID: [bold green]{task_id}[/]")
        else:
            console.print(f"[bold red]Error:[/] Schedule with ID '{schedule_id}' not found or task could not be enqueued.")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error running schedule '{schedule_id}':[/] {e}")
        raise typer.Exit(code=1) from e

@schedule_app.command("pause")
def pause_schedule(
    schedule_id: str = typer.Argument(..., help="The ID of the schedule to pause."),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
):
    """Pause a running schedule."""
    _toggle_schedule_pause(schedule_id, schedule_storage_url, pause=True)


@schedule_app.command("resume")
def resume_schedule(
    schedule_id: str = typer.Argument(..., help="The ID of the schedule to resume."),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
):
    """Resume a paused schedule."""
    _toggle_schedule_pause(schedule_id, schedule_storage_url, pause=False)

def main():
    """The main entry point for the CLI script."""
    app()


@app.command(name="run-dashboard")
def run_dashboard(
    host: str = typer.Option("127.0.0.1", "--host", help="Host address to bind to."),
    port: int = typer.Option(8000, "--port", help="Port to listen on."),
    task_queue_url: Optional[str] = typer.Option(
        None,
        "--task-queue-url",
        help="URL for the task queue backend (overrides OMNIQ_TASK_QUEUE_URL).",
    ),
    result_storage_url: Optional[str] = typer.Option(
        None,
        "--result-storage-url",
        help="URL for the result storage backend (overrides OMNIQ_RESULT_STORAGE_URL).",
    ),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level (e.g., DEBUG, INFO, WARNING)."
    ),
):
    """
    Start the OmniQ web dashboard.
    """
    # Ensure logging is configured before uvicorn takes over
    # Uvicorn's default logging can be quite verbose, so setting a base level here helps.
    # The log_level option for uvicorn itself will control its output.
    logging.getLogger().setLevel(log_level.upper())
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("omniq.cli")

    logger.info("Initializing OmniQ dashboard...")
    logger.info(f"  Listening on: http://{host}:{port}")

    try:
        # Initialize OmniQ instance to be passed to the Litestar app
        omniq_instance = OmniQ(
            task_queue_url=task_queue_url,
            result_storage_url=result_storage_url,
            schedule_storage_url=schedule_storage_url,
        )
        app_instance = create_app(omniq_instance)
        import uvicorn
        uvicorn.run(app_instance, host=host, port=port, log_level=log_level.lower())
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}", exc_info=True)
        raise typer.Exit(code=1) from e

    logger.info("Dashboard has shut down.")


@app.command(name="run-scheduler")
def run_scheduler(
    check_interval: float = typer.Option(
        5.0, "--interval", "-i", help="Interval in seconds to check for due schedules."
    ),
    task_queue_url: Optional[str] = typer.Option(
        None,
        "--task-queue-url",
        help="URL for the task queue backend (overrides OMNIQ_TASK_QUEUE_URL).",
    ),
    result_storage_url: Optional[str] = typer.Option(
        None,
        "--result-storage-url",
        help="URL for the result storage backend (overrides OMNIQ_RESULT_STORAGE_URL).",
    ),
    schedule_storage_url: Optional[str] = typer.Option(
        None,
        "--schedule-storage-url",
        help="URL for the schedule storage backend (overrides OMNIQ_SCHEDULE_STORAGE_URL).",
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level (e.g., DEBUG, INFO, WARNING)."
    ),
):
    """
    Start the OmniQ scheduler to enqueue scheduled tasks.
    """
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("omniq.cli")

    logger.info("Initializing OmniQ scheduler...")
    logger.info(f"  Check Interval: {check_interval} seconds")

    try:
        omniq_instance = OmniQ(
            task_queue_url=task_queue_url,
            result_storage_url=result_storage_url,
            schedule_storage_url=schedule_storage_url,
        )
        scheduler = Scheduler(omniq_instance, check_interval=check_interval)
        asyncio.run(scheduler.run())
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise typer.Exit(code=1) from e

    logger.info("Scheduler has shut down.")