import os
import pytest
from unittest.mock import patch
import run_bot
import scheduler
from gartan_fetch import AuthenticationError

def test_run_bot_auth_lock_exit(tmp_path):
    # Setup lock file
    lock_file = tmp_path / "AUTH_LOCK"
    lock_file.write_text("2024-01-01 12:00:00")

    with patch("run_bot.is_auth_locked", return_value=True):
        with patch("run_bot.config.auth_lock_path", str(lock_file)):
            with pytest.raises(SystemExit) as e:
                run_bot.main()
            assert e.value.code == 2

def test_scheduler_auth_lock_exit(tmp_path):
    # Setup lock file
    lock_file = tmp_path / "AUTH_LOCK"
    lock_file.write_text("2024-01-01 12:00:00")

    with patch("scheduler.is_auth_locked", return_value=True):
        with patch("scheduler.get_auth_lock_info", return_value="2024-01-01 12:00:00"):
            with patch("scheduler.config.auth_lock_path", str(lock_file)):
                with pytest.raises(SystemExit) as e:
                    scheduler.check_auth_lock()
                assert e.value.code == 2

def test_scheduler_no_auth_lock_does_not_exit():
    with patch("scheduler.is_auth_locked", return_value=False):
        # This should not raise SystemExit
        scheduler.check_auth_lock()

@patch("run_bot.gartan_login_and_get_session")
def test_run_bot_creates_lock_on_auth_error(mock_login, tmp_path):
    mock_login.side_effect = AuthenticationError("Invalid username or password", is_credential_failure=True)

    lock_file = tmp_path / "AUTH_LOCK"
    if lock_file.exists():
        os.remove(lock_file)

    with patch("run_bot.config.auth_lock_path", str(lock_file)):
        with patch("sys.argv", ["run_bot.py", "--max-days", "1"]):
            with pytest.raises(SystemExit) as e:
                run_bot.main()
            assert e.value.code == 2
            assert lock_file.exists()

@patch("run_bot.gartan_login_and_get_session")
def test_run_bot_does_not_create_lock_on_non_credential_auth_error(mock_login, tmp_path):
    mock_login.side_effect = AuthenticationError("Some other reason", is_credential_failure=False)

    lock_file = tmp_path / "AUTH_LOCK"
    if lock_file.exists():
        os.remove(lock_file)

    with patch("run_bot.config.auth_lock_path", str(lock_file)):
        with patch("sys.argv", ["run_bot.py", "--max-days", "1"]):
            # For non-credential error, run_bot might continue or exit depending on other logic,
            # but it should NOT exit with code 2 and NOT create a lock file.
            try:
                run_bot.main()
            except SystemExit as e:
                assert e.code != 2
            except Exception:
                pass

            assert not lock_file.exists()
