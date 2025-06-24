async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch error:', error);
        return null;
    }
}

function showEnqueueForm() {
    document.getElementById('forms').style.display = 'block';
    document.getElementById('enqueue-form').style.display = 'block';
    document.getElementById('schedule-form').style.display = 'none';
}

function showScheduleForm() {
    document.getElementById('forms').style.display = 'block';
    document.getElementById('enqueue-form').style.display = 'none';
    document.getElementById('schedule-form').style.display = 'block';
}

function hideForms() {
    document.getElementById('forms').style.display = 'none';
    document.getElementById('enqueue-form').style.display = 'none';
    document.getElementById('schedule-form').style.display = 'none';
}

async function refreshTasks() {
    const tasks = await fetchData('/tasks');
    if (tasks) {
        const taskList = document.getElementById('task-list');
        taskList.innerHTML = '';
        tasks.forEach(task => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${task.id}</td>
                <td>${task.name}</td>
                <td>${task.status}</td>
                <td>
                    <button onclick="cancelTask('${task.id}')">Cancel</button>
                    <button onclick="viewResult('${task.id}')">View Result</button>
                </td>
            `;
            taskList.appendChild(row);
        });
    }
}

async function refreshSchedules() {
    const schedules = await fetchData('/schedules');
    if (schedules) {
        const scheduleList = document.getElementById('schedule-list');
        scheduleList.innerHTML = '';
        schedules.forEach(schedule => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${schedule.id}</td>
                <td>${schedule.name}</td>
                <td>${schedule.status}</td>
                <td>
                    <button onclick="toggleSchedule('${schedule.id}', '${schedule.status}')">
                        ${schedule.status === 'active' ? 'Pause' : 'Resume'}
                    </button>
                </td>
            `;
            scheduleList.appendChild(row);
        });
    }
}

async function enqueueTask(event) {
    event.preventDefault();
    const taskName = document.getElementById('task-name').value;
    const taskData = document.getElementById('task-data').value;
    try {
        const task = JSON.parse(taskData);
        task.name = taskName;
        const response = await fetch('/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(task),
        });
        if (response.ok) {
            const result = await response.json();
            alert(`Task enqueued with ID: ${result.task_id}`);
            hideForms();
            refreshTasks();
        } else {
            alert('Failed to enqueue task');
        }
    } catch (error) {
        console.error('Error enqueuing task:', error);
        alert('Invalid task data format');
    }
}

async function addSchedule(event) {
    event.preventDefault();
    const scheduleName = document.getElementById('schedule-name').value;
    const scheduleCron = document.getElementById('schedule-cron').value;
    const scheduleTaskData = document.getElementById('schedule-task-data').value;
    try {
        const taskData = JSON.parse(scheduleTaskData);
        const schedule = {
            name: scheduleName,
            cron: scheduleCron,
            task_data: taskData,
        };
        const response = await fetch('/schedules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(schedule),
        });
        if (response.ok) {
            const result = await response.json();
            alert(`Schedule added with ID: ${result.schedule_id}`);
            hideForms();
            refreshSchedules();
        } else {
            alert('Failed to add schedule');
        }
    } catch (error) {
        console.error('Error adding schedule:', error);
        alert('Invalid schedule data format');
    }
}

async function cancelTask(taskId) {
    const response = await fetch(`/tasks/${taskId}`, {
        method: 'DELETE',
    });
    if (response.ok) {
        const result = await response.json();
        alert(result.status);
        refreshTasks();
    } else {
        alert('Failed to cancel task');
    }
}

async function viewResult(taskId) {
    const result = await fetchData(`/results/${taskId}`);
    if (result) {
        if (result.error) {
            alert(result.error);
        } else {
            alert(`Result for Task ${taskId}: ${JSON.stringify(result, null, 2)}`);
        }
    } else {
        alert('Failed to fetch result');
    }
}

async function toggleSchedule(scheduleId, status) {
    const action = status === 'active' ? 'pause' : 'resume';
    const response = await fetch(`/schedules/${scheduleId}/${action}`, {
        method: 'PUT',
    });
    if (response.ok) {
        const result = await response.json();
        alert(result.status);
        refreshSchedules();
    } else {
        alert(`Failed to ${action} schedule`);
    }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    refreshTasks();
    refreshSchedules();
});
