import time
from datetime import datetime, timezone
from typing import List, Optional

import htpy as h

from omniq.models import Schedule, Task, TaskResult
from omniq.serialization import default_serializer


def base_html(*children: h.AnyChild) -> str:
    """A basic HTML template for the dashboard."""
    return str(
        h.html[
            h.head[
                h.meta(charset="utf-8"),
                h.meta(name="viewport", content="width=device-width, initial-scale=1"),
                h.title["OmniQ Dashboard"],
                h.script(src="https://unpkg.com/htmx.org@1.9.10"),
                h.script(src="https://unpkg.com/datastar@0.0.14/dist/datastar.js"),
                h.style[
                    """
                    body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
                    h1 { color: #0056b3; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #fff; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #0056b3; color: white; }
                    tr:nth-child(even) { background-color: #f2f2f2; }
                    .status-paused { color: orange; font-weight: bold; }
                    .status-active { color: green; font-weight: bold; }
                    .status-pending { color: blue; }
                    .status-waiting { color: gray; }
                    .status-success { color: green; }
                    .status-failure { color: red; font-weight: bold; }
                    """
                ],
            ],
            h.body[*children],
        ]
    )


def schedules_table(schedules: List[Schedule]) -> h.Element:
    """Renders the schedules table."""
    rows = []
    for s in schedules:
        next_run_str = "N/A"
        if s.next_run_at:
            next_run_dt = datetime.fromtimestamp(s.next_run_at, tz=timezone.utc)
            next_run_str = next_run_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')

        last_run_str = "Never"
        if s.last_run_at:
            last_run_dt = datetime.fromtimestamp(s.last_run_at, tz=timezone.utc)
            last_run_str = last_run_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')

        status_class = "status-paused" if s.is_paused else "status-active"
        status_text = "Paused" if s.is_paused else "Active" # Changed to string literal for display
        rows.append(
            h.tr[
                h.td[s.id],
                h.td[s.task.queue],
                h.td[s.cron or f"every {s.interval}s"],
                h.td[f"{s.task.func.__module__}.{s.task.func.__name__}"],
                h.td[next_run_str],
                h.td[last_run_str],
                h.td[h.span(class_=status_class)[status_text]], # Corrected htpy syntax for span content
            ]
        )

    return h.div[
        h.h2["Scheduled Tasks"],
        h.table[
            h.thead[
                h.tr[
                    h.th["ID"],
                    h.th["Queue"],
                    h.th["Schedule"],
                    h.th["Task Function"],
                    h.th["Next Run (UTC)"],
                    h.th["Last Run (UTC)"],
                    h.th["Status"],
                    h.th["Actions"],
                ]
            ],
            h.tbody[*rows],
        ]
    ]


def results_table(results: List[TaskResult]) -> h.Element:
    """Renders the recent results table."""
    if not results:
        return h.div[
            h.h2["Recent Task Results"],
            h.p["No recent results found."]
        ]

    rows = []
    for r in results:
        completed_at_str = "N/A"
        if r.completed_at:
            completed_at_dt = datetime.fromtimestamp(r.completed_at, tz=timezone.utc)
            completed_at_str = completed_at_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')

        status_class = "status-success" if r.status == "SUCCESS" else "status-failure"

        # Truncate result for display
        try:
            result_val = default_serializer.deserialize(r.result)
            result_str = str(result_val)
            if len(result_str) > 100:
                result_str = result_str[:100] + "..."
        except Exception:
            result_str = "[Deserialization Error]"

        rows.append(
            h.tr[
                h.td[r.task_id],
                h.td[h.span(class_=status_class)[r.status]], # Corrected htpy syntax for span content
                h.td[completed_at_str],
                h.td[r.worker_id or "N/A"],
                h.td(title=str(result_val))[result_str], # Corrected htpy syntax for td content
            ]
        )

    return h.div[
        h.h2["Recent Task Results"],
        h.table[
            h.thead[
                h.tr[
                    h.th["Task ID"],
                    h.th["Status"],
                    h.th["Completed At (UTC)"],
                    h.th["Worker ID"],
                    h.th["Result"],
                ]
            ],
            h.tbody[*rows],
        ]
    ]


def pending_tasks_table(tasks: List[Task]) -> h.Element:
    """Renders the pending tasks table."""
    if not tasks:
        return h.div[
            h.h2["Pending Tasks"],
            h.p["No pending tasks found."]
        ]

    rows = []
    for t in tasks:
        created_at_str = datetime.fromtimestamp(t.created_at, tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        status_class = f"status-{t.status}"
        rows.append(
            h.tr[
                h.td[t.id],
                h.td[t.queue],
                h.td[f"{t.func.__module__}.{t.func.__name__}"],
                h.td[str(t.args)],
                h.td[str(t.kwargs)],
                h.td[created_at_str],
                h.td[h.span(class_=status_class)[t.status.capitalize()]],
                h.td[", ".join(t.dependencies) if t.dependencies else "None"],
                h.td[str(t.dependencies_left)],
            ]
        )

    return h.div[
        h.h2["Pending Tasks"],
        h.table[
            h.thead[
                h.tr[
                    h.th["ID"],
                    h.th["Queue"],
                    h.th["Function"],
                    h.th["Args"],
                    h.th["Kwargs"],
                    h.th["Created At (UTC)"],
                    h.th["Status"],
                    h.th["Dependencies"],
                    h.th["Deps Left"],
                ]
            ],
            h.tbody[*rows],
        ]
    ]


def failed_tasks_table(tasks: List[Task]) -> h.Element:
    """Renders the failed tasks table."""
    if not tasks:
        return h.div[
            h.h2["Failed Tasks"],
            h.p["No failed tasks found."]
        ]

    rows = []
    for t in tasks:
        created_at_str = datetime.fromtimestamp(t.created_at, tz=timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        rows.append(
            h.tr[
                h.td[t.id],
                h.td[t.queue],
                h.td[f"{t.func.__module__}.{t.func.__name__}"],
                h.td[created_at_str],
                h.td[str(t.retries)],
                h.td[str(t.max_retries)],
            ]
        )

    return h.div[
        h.h2["Failed Tasks"],
        h.table[
            h.thead[h.tr[h.th["ID"], h.th["Queue"], h.th["Function"], h.th["Created At (UTC)"], h.th["Retries"], h.th["Max Retries"]]],
            h.tbody[*rows],
        ]
    ]


def workers_status_section() -> h.Element:
    """Renders a section describing OmniQ workers."""
    return h.div[
        h.h2["OmniQ Workers"],
        h.p[
            "OmniQ workers are independent processes or threads that consume tasks from queues. "
            "You can start them using the ", h.code["omniq run-worker"], " CLI command."
        ],
        h.ul[
            h.li[h.strong["AsyncWorker"], ": Ideal for I/O-bound tasks."],
            h.li[h.strong["ThreadPoolWorker"], ": Suitable for CPU-bound or blocking I/O tasks."],
            h.li[h.strong["ProcessPoolWorker"], ": Best for CPU-bound tasks, leveraging multiple CPU cores."],
        ],
        h.div(id="worker_metrics_container")[
            h.h3["Live Worker Metrics (Coming Soon)"],
            h.p[
                "For real-time worker metrics (e.g., active workers, tasks processed per worker), "
                "a custom worker heartbeat and reporting mechanism would be required. "
                "This section will be enhanced in future updates."
            ]
        ]
    ]


def dashboard_page() -> str:
    """Generates the full dashboard HTML page."""
    return base_html(
        h.h1["OmniQ Dashboard"],
        h.div(
            id="schedules_container",
            # Initial content will be empty, datastar will populate it via SSE
            # hx-ext="sse" and ds-stream will connect to the /events endpoint
            # and update this div.
            **{
                "hx-ext": "sse",
                "sse-connect": "/events",
                "ds-stream": "schedules_container",
            },
        )[
            h.p["Loading schedules..."],
        ],
        workers_status_section(), # New section for worker status
        h.div(
            id="results_container",
            # This div will also be updated by the SSE stream
            **{"ds-stream": "results_container"},
        )[
            h.p["Loading recent results..."],
        ],
        h.div(
            id="pending_tasks_container",
            **{"ds-stream": "pending_tasks_container"},
        )[
            h.p["Loading pending tasks..."],
        ],
        h.div(
            id="failed_tasks_container",
            **{"ds-stream": "failed_tasks_container"},
        )[
            h.p["Loading failed tasks..."],
        ],
        h.div(id="last_updated_display", **{"ds-stream": "last_updated_display"})[ # Corrected htpy syntax for div content
            h.p[f"Last updated: {datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}"], # Corrected htpy syntax for p content
        ]
    )