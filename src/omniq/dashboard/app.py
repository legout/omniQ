import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from datastar import Server
from litestar import Litestar, get
from litestar.response import ServerSentEvent
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from omniq.core import OmniQ
from omniq.dashboard.views import dashboard_page, results_table, schedules_table

logger = logging.getLogger(__name__)


async def get_dashboard_data(omniq_instance: OmniQ) -> Dict[str, Any]:
    """Fetches and formats data for the dashboard."""
    schedules_task = omniq_instance.list_schedules()  # type: ignore
    results_task = omniq_instance.list_recent_results(limit=20)  # type: ignore
    pending_tasks_task = omniq_instance.list_pending_tasks(limit=20)  # type: ignore
    failed_tasks_task = omniq_instance.list_failed_tasks(limit=20)  # type: ignore

    schedules, recent_results, pending_tasks, failed_tasks = await asyncio.gather(
        schedules_task, results_task, pending_tasks_task, failed_tasks_task
    )

    # Sort schedules by next run time for better display
    schedules.sort(key=lambda s: s.next_run_at if s.next_run_at else float('inf'))

    # For a basic dashboard, we'll just pass the schedules directly.
    # More complex dashboards would involve fetching task counts, recent results, etc.
    return {
        "schedules": schedules,
        "pending_tasks": pending_tasks,
        "failed_tasks": failed_tasks,
        "recent_results": recent_results,
        "last_updated": time.time(),
    }


@get("/")
async def index() -> str:
    """Serves the main dashboard HTML page."""
    return dashboard_page()


@get("/events", status_code=HTTP_200_OK)
async def events(omniq: OmniQ) -> ServerSentEvent:
    """Server-Sent Events endpoint for live dashboard updates."""
    datastar_server = Server()

    async def event_generator():
        last_data = {}
        while True:
            try:
                current_data = await get_dashboard_data(omniq)

                # Only send updates if data has changed
                if current_data != last_data:
                    updates = {}
                    # Render the schedules table
                    schedules_html = schedules_table(current_data["schedules"])
                    updates["schedules_container"] = schedules_html

                    # Render the results table
                    results_html = results_table(current_data["recent_results"])
                    updates["results_container"] = results_html

                    # Render the pending tasks table
                    pending_html = schedules_table(current_data["pending_tasks"])
                    updates["pending_tasks_container"] = pending_html

                    # Render the failed tasks table
                    failed_html = schedules_table(current_data["failed_tasks"])
                    updates["failed_tasks_container"] = failed_html

                    # Render the last updated time
                    last_updated_str = datetime.fromtimestamp(current_data["last_updated"], tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
                    updates["last_updated_display"] = f"<p>Last updated: {last_updated_str}</p>"

                    yield datastar_server.update(updates)
                    last_data = current_data

            except Exception as e:
                logger.error(f"Error in SSE event generator: {e}", exc_info=True)

            await asyncio.sleep(1)  # Update every second

    return ServerSentEvent(event_generator())


@post("/schedules/{schedule_id:str}/pause", status_code=HTTP_204_NO_CONTENT)
async def pause_schedule_endpoint(schedule_id: str, omniq: OmniQ) -> None:
    """API endpoint to pause a schedule."""
    logger.info(f"Attempting to pause schedule: {schedule_id}")
    await omniq.pause_schedule(schedule_id)
    logger.info(f"Schedule {schedule_id} paused.")


@post("/schedules/{schedule_id:str}/resume", status_code=HTTP_204_NO_CONTENT)
async def resume_schedule_endpoint(schedule_id: str, omniq: OmniQ) -> None:
    """API endpoint to resume a schedule."""
    logger.info(f"Attempting to resume schedule: {schedule_id}")
    await omniq.resume_schedule(schedule_id)
    logger.info(f"Schedule {schedule_id} resumed.")


@post("/schedules/{schedule_id:str}/run", status_code=HTTP_204_NO_CONTENT)
async def run_schedule_now_endpoint(schedule_id: str, omniq: OmniQ) -> None:
    """API endpoint to run a schedule's task immediately."""
    logger.info(f"Attempting to run schedule {schedule_id} immediately.")
    schedule = await omniq.get_schedule(schedule_id)
    if schedule:
        try:
            # Enqueue the task associated with the schedule
            task_id = await omniq.enqueue(
                func=schedule.task.func,
                *schedule.task.args,
                queue=schedule.task.queue,
                **schedule.task.kwargs,
            )
            logger.info(f"Task {task_id} enqueued from schedule {schedule_id}.")
        except Exception as e:
            logger.error(f"Failed to enqueue task for schedule {schedule_id}: {e}", exc_info=True)
    else:
        logger.warning(f"Schedule {schedule_id} not found for 'run now' action.")


def create_app(omniq_instance: OmniQ) -> Litestar:
    """Creates and configures the Litestar application."""
    return Litestar(
        route_handlers=[
            index, events, pause_schedule_endpoint, resume_schedule_endpoint, run_schedule_now_endpoint
        ],
        dependencies={"omniq": lambda: omniq_instance},  # Inject OmniQ instance
    )