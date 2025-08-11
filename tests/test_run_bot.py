import os
import subprocess
import sys

import pytest


def test_run_bot_cli(tmp_path):
    # Create a dummy crew_details.local
    crew_details = tmp_path / "crew_details.local"
    crew_details.write_text("John Doe|John Doe|123456789\n")
    # Run the bot with cache-only and max-days=1
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "run_bot.py", "--cache-only", "--max-days", "1"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (
        "Saved crew details" in result.stdout
        or "Saved appliance availability" in result.stdout
    )


def test_run_bot_cli_cache_preferred(tmp_path):
    crew_details = tmp_path / "crew_details.local"
    crew_details.write_text("Jane Doe|Jane Doe|987654321\n")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "run_bot.py", "--cache-only", "--max-days", "1"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (
        "Saved crew details" in result.stdout
        or "Saved appliance availability" in result.stdout
    )


def test_run_bot_cli_cache_off(tmp_path):
    crew_details = tmp_path / "crew_details.local"
    crew_details.write_text("Alex|Alex|555555555\n")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "run_bot.py", "--max-days", "1"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert (
        "Saved crew details" in result.stdout
        or "Saved appliance availability" in result.stdout
    )


def test_run_bot_cli_missing_crew_details(tmp_path):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "run_bot.py", "--cache-only", "--max-days", "1"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    # Should fallback to default/test crew details or print a warning
    assert result.returncode == 0
    assert "crew" in result.stdout.lower() or "appliance" in result.stdout.lower()


def test_run_bot_cli_invalid_args(tmp_path):
    crew_details = tmp_path / "crew_details.local"
    crew_details.write_text("John Doe|John Doe|123456789\n")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    result = subprocess.run(
        [sys.executable, "run_bot.py", "--bad-arg"],
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert (
        result.returncode != 0
        or "usage" in result.stdout.lower()
        or "usage" in result.stderr.lower()
        or "error" in result.stdout.lower()
        or "error" in result.stderr.lower()
    )
