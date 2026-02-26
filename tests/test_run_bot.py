import os
import subprocess
import sys


def _subprocess_env(extra=None):
    env = os.environ.copy()
    # Provide dummy credentials so run_bot does not assert
    env.setdefault("GARTAN_USERNAME", "dummy_user")
    env.setdefault("GARTAN_PASSWORD", "dummy_pass")
    if extra:
        env.update(extra)
    return env


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
        env=_subprocess_env(),
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
        env=_subprocess_env(),
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
        env=_subprocess_env(),
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
        env=_subprocess_env(),
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
        env=_subprocess_env(),
    )
    assert (
        result.returncode != 0
        or "usage" in result.stdout.lower()
        or "usage" in result.stderr.lower()
        or "error" in result.stdout.lower()
        or "error" in result.stderr.lower()
    )


def test_cleanup_old_cache_files_nonexistent_dir():
    """Test cleanup_old_cache_files with non-existent directory."""
    from datetime import datetime

    from run_bot import cleanup_old_cache_files

    # Test with non-existent directory (lines 37-38)
    cleanup_old_cache_files("/nonexistent/path", datetime.now())
    # Should not raise exception, just log and return


def test_cleanup_old_cache_files_with_error(tmp_path, monkeypatch):
    """Test cleanup_old_cache_files with file processing errors."""
    from datetime import datetime

    from run_bot import cleanup_old_cache_files

    # Create a file with cache naming pattern
    cache_file = tmp_path / "grid_05-08-2025.html"
    cache_file.write_text("test")

    # Mock os.remove to raise an exception (lines 49-50)
    def mock_remove(path):
        raise PermissionError("Access denied")

    monkeypatch.setattr("run_bot.os.remove", mock_remove)

    # Should handle the exception gracefully
    today = datetime.now()
    cleanup_old_cache_files(str(tmp_path), today)
    # Should not raise exception, just log warning
