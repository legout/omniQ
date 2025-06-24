from litestar import Litestar, get, post, delete, put, WebSocket
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.static_files import create_static_files_router
from litestar.di import Provide
from omniq.queue.async_task_queue import AsyncTaskQueue
from omniq.models.task import Task
from omniq.models.schedule import Schedule
import asyncio
import json
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dependency injection for task queue
async def provide_task_queue() -> AsyncTaskQueue:
    return AsyncTaskQueue(
        task_queue_type="memory",
        worker_type="async",
        max_workers=10
    )

# Dashboard routes
@get("/")
async def index(task_queue: AsyncTaskQueue) -> Template:
    tasks = await task_queue.get_all_tasks()
    return Template("index.html", tasks=tasks, title="OmniQ Dashboard")

@get("/tasks")
async def get_tasks(task_queue: AsyncTaskQueue) -> List[Dict[str, Any]]:
    tasks = await task_queue.get_all_tasks()
    return [task.dict() for task in tasks]

@get("/schedules")
async def get_schedules(task_queue: AsyncTaskQueue) -> List[Dict[str, Any]]:
    scheduler = task_queue.scheduler
    schedules = await scheduler.get_all_schedules()
    return [schedule.dict() for schedule in schedules]

@post("/tasks")
async def enqueue_task(data: Dict[str, Any], task_queue: AsyncTaskQueue) -> Dict[str, str]:
    task = Task.from_dict(data)
    task_id = await task_queue.enqueue_task(task)
    return {"task_id": task_id}

@post("/schedules")
async def add_schedule(data: Dict[str, Any], task_queue: AsyncTaskQueue) -> Dict[str, str]:
    schedule = Schedule.from_dict(data)
    scheduler = task_queue.scheduler
    schedule_id = await scheduler.add_schedule(schedule)
    return {"schedule_id": schedule_id}

@put("/schedules/{schedule_id:str}/pause")
async def pause_schedule(schedule_id: str, task_queue: AsyncTaskQueue) -> Dict[str, str]:
    scheduler = task_queue.scheduler
    await scheduler.pause_schedule(schedule_id)
    return {"status": f"Schedule {schedule_id} paused"}

@put("/schedules/{schedule_id:str}/resume")
async def resume_schedule(schedule_id: str, task_queue: AsyncTaskQueue) -> Dict[str, str]:
    scheduler = task_queue.scheduler
    await scheduler.resume_schedule(schedule_id)
    return {"status": f"Schedule {schedule_id} resumed"}

@delete("/tasks/{task_id:str}")
async def cancel_task(task_id: str, task_queue: AsyncTaskQueue) -> Dict[str, str]:
    await task_queue.cancel_task(task_id)
    return {"status": f"Task {task_id} cancelled"}

@get("/metrics")
async def get_metrics(task_queue: AsyncTaskQueue) -> Dict[str, Any]:
    return {
        "total_tasks": await task_queue.get_task_count(),
        "running_tasks": await task_queue.get_running_task_count(),
        "completed_tasks": await task_queue.get_completed_task_count(),
        "failed_tasks": await task_queue.get_failed_task_count(),
    }

@get("/results/{task_id:str}")
async def get_result(task_id: str, task_queue: AsyncTaskQueue) -> Dict[str, Any]:
    result = await task_queue.get_result(task_id)
    return result.dict() if result else {"error": "Result not found"}

@WebSocket("/ws")
async def websocket_endpoint(socket: WebSocket, task_queue: AsyncTaskQueue) -> None:
    await socket.accept()
    try:
        while True:
            metrics = await get_metrics(task_queue)
            await socket.send_json(metrics)
            await asyncio.sleep(5)  # Send updates every 5 seconds
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await socket.close()

# Create Litestar app
app = Litestar(
    route_handlers=[
        index,
        get_tasks,
        get_schedules,
        enqueue_task,
        add_schedule,
        pause_schedule,
        resume_schedule,
        cancel_task,
        get_metrics,
        get_result,
        websocket_endpoint,
        create_static_files_router("/static", directories=["static"]),
    ],
    dependencies={"task_queue": Provide(provide_task_queue)},
    template_engine=JinjaTemplateEngine,
    template_config={"directory": "templates"},
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
