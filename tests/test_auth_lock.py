import os
from unittest.mock import patch

import pytest

import run_bot
import scheduler


def test_run_bot_auth_lock_exit(tmp_path):
    # Setup lock file
    lock_file = tmp_path / "AUTH_LOCK"
    lock_file.write_text("2024-01-01 12:00:00")

    with patch("run_bot.config.auth_lock_path", str(lock_file)):
        with pytest.raises(SystemExit) as e:
            run_bot.main()
        assert e.value.code == 2


def test_scheduler_auth_lock_exit(tmp_path):
    # Setup lock file
    lock_file = tmp_path / "AUTH_LOCK"
    lock_file.write_text("2024-01-01 12:00:00")

    with patch("scheduler.config.auth_lock_path", str(lock_file)):
        with pytest.raises(SystemExit) as e:
            scheduler.check_auth_lock()
        assert e.value.code == 2


@patch("run_bot.gartan_login_and_get_session")
def test_run_bot_creates_lock_on_auth_error(mock_login, tmp_path):
    from gartan_fetch import AuthenticationError

    mock_login.side_effect = AuthenticationError("Invalid username or password")

    lock_file = tmp_path / "AUTH_LOCK"
    if lock_file.exists():
        os.remove(lock_file)

    with patch("run_bot.config.auth_lock_path", str(lock_file)):
        with patch("sys.argv", ["run_bot.py", "--max-days", "1"]):
            with pytest.raises(SystemExit) as e:
                run_bot.main()
            assert e.value.code == 2
            assert lock_file.exists()
