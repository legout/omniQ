import pytest
from typer.testing import CliRunner

from omniq.cli import app
from omniq.models import Schedule, Task
from tests.helpers import sync_add

# --- Fixtures ---


@pytest.fixture
def runner():
    """Provides a Typer CliRunner instance."""
    return CliRunner()


# --- Tests ---


def test_schedule_add_list_remove(runner: CliRunner, omniq_instance):
    """
    Test the full lifecycle of a schedule via the CLI: add, list, and remove.
    This test uses the in-memory backend provided by the omniq_instance fixture.
    """
    # We need to patch OmniQ to return our pre-configured in-memory instance
    # instead of creating a new one.
    from omniq import cli
    from unittest.mock import patch

    with patch.object(cli, "OmniQ", return_value=omniq_instance):
        # --- ADD ---
        result_add = runner.invoke(
            app,
            [
                "schedule",
                "add",
                "tests.helpers:sync_add",
                "--interval",
                "60",
                "--args",
                "[1, 2]",
            ],
        )
        assert result_add.exit_code == 0
        assert "Successfully added schedule with ID" in result_add.stdout

        # Verify it was added in the backend
        schedules = omniq_instance.list_schedules_sync()
        assert len(schedules) == 1
        schedule_id = schedules[0].id

        # --- LIST ---
        result_list = runner.invoke(app, ["schedule", "list"])
        assert result_list.exit_code == 0
        assert schedule_id in result_list.stdout
        assert "tests.helpers.sync_add" in result_list.stdout
        assert "every 60.0s" in result_list.stdout

        # --- REMOVE ---
        result_remove = runner.invoke(app, ["schedule", "remove", schedule_id])
        assert result_remove.exit_code == 0
        assert f"Successfully removed schedule with ID: {schedule_id}" in result_remove.stdout

        # Verify it was removed from the backend
        schedules_after_remove = omniq_instance.list_schedules_sync()
        assert len(schedules_after_remove) == 0


def test_schedule_pause_resume(runner: CliRunner, omniq_instance):
    """Test pausing and resuming a schedule via the CLI."""
    from omniq import cli
    from unittest.mock import patch

    # Add a schedule to the backend directly
    task = Task(func=sync_add, args=(1, 1))
    schedule = Schedule(task=task, interval=60, is_paused=False)
    omniq_instance.add_schedule_sync(schedule)

    with patch.object(cli, "OmniQ", return_value=omniq_instance):
        # --- PAUSE ---
        result_pause = runner.invoke(app, ["schedule", "pause", schedule.id])
        assert result_pause.exit_code == 0
        assert f"Successfully paused schedule with ID: {schedule.id}" in result_pause.stdout

        # Verify state in backend
        paused_schedule = omniq_instance.get_schedule_sync(schedule.id)
        assert paused_schedule.is_paused is True

        # --- PAUSE AGAIN (should be idempotent) ---
        result_pause_again = runner.invoke(app, ["schedule", "pause", schedule.id])
        assert result_pause_again.exit_code == 0
        assert "is already paused" in result_pause_again.stdout

        # --- RESUME ---
        result_resume = runner.invoke(app, ["schedule", "resume", schedule.id])
        assert result_resume.exit_code == 0
        assert f"Successfully resumed schedule with ID: {schedule.id}" in result_resume.stdout

        # Verify state in backend
        resumed_schedule = omniq_instance.get_schedule_sync(schedule.id)
        assert resumed_schedule.is_paused is False

        # --- RESUME AGAIN (should be idempotent) ---
        result_resume_again = runner.invoke(app, ["schedule", "resume", schedule.id])
        assert result_resume_again.exit_code == 0
        assert "is already active" in result_resume_again.stdout


def test_schedule_cli_errors(runner: CliRunner, omniq_instance):
    """Test various error conditions for the schedule CLI."""
    from omniq import cli
    from unittest.mock import patch

    with patch.object(cli, "OmniQ", return_value=omniq_instance):
        # Add with both cron and interval
        result = runner.invoke(
            app,
            ["schedule", "add", "tests.helpers:sync_add", "--interval", "10", "--cron", "* * * * *"],
        )
        assert result.exit_code == 1
        assert "Cannot provide both --cron and --interval" in result.stdout

        # Add with bad function import string
        result = runner.invoke(
            app,
            ["schedule", "add", "bad.module:nonexistent_func", "--interval", "10"],
        )
        assert result.exit_code == 1
        assert "Could not import" in result.stdout

        # Remove non-existent schedule
        result = runner.invoke(app, ["schedule", "remove", "non-existent-id"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

        # Pause non-existent schedule
        result = runner.invoke(app, ["schedule", "pause", "non-existent-id"])
        assert result.exit_code == 1
        assert "not found" in result.stdout

        # Resume non-existent schedule
        result = runner.invoke(app, ["schedule", "resume", "non-existent-id"])
        assert result.exit_code == 1
        assert "not found" in result.stdout