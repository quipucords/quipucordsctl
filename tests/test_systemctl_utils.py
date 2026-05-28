"""Test the systemctl_utils module."""

import os
import subprocess
from unittest import mock

import pytest

from quipucordsctl import settings, systemctl_utils


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(systemctl_utils, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_reload_daemon(mock_shell_utils):
    """Test reload_daemon invokes expected shell commands."""
    assert systemctl_utils.reload_daemon()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(settings.SYSTEMCTL_USER_RESET_FAILED_CMD),
            mock.call(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD),
        )
    )


def test_stop_service(mock_shell_utils):
    """Test stop_service invokes expected Podman commands."""
    mock_shell_utils.run_command.side_effect = [
        ["", "", 0],
        ["", "", 1],
        ["", "", 1],
    ]

    assert systemctl_utils.stop_service()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(settings.SYSTEMCTL_USER_LIST_QUIPUCORDS_APP, raise_error=False),
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP),
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK),
        )
    )


def test_stop_service_failed_systemctl(mock_shell_utils):
    """Test stop_service to return false if systemctl failed."""
    mock_shell_utils.run_command.side_effect = [
        ["", "", 0],
        ["", "", 1],
        Exception("systemctl_failed"),
    ]

    assert not systemctl_utils.stop_service()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(settings.SYSTEMCTL_USER_LIST_QUIPUCORDS_APP, raise_error=False),
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP),
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK),
        )
    )


@mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1234"}, clear=True)
def test_valid_systemd_user_session(mock_shell_utils):
    """Test ensure_systemd_user_session - happy path."""
    mock_shell_utils.run_command.return_value = ("", "", 0)
    assert not systemctl_utils.ensure_systemd_user_session()
    mock_shell_utils.run_command.assert_called_once_with(
        settings.SYSTEMCTL_USER_IS_SYSTEM_RUNNING_CMD
    )


@mock.patch.dict(os.environ, {}, clear=True)
def test_invalid_systemd_user_session_no_env(mock_shell_utils):
    """Test ensure_systemd_user_session - environment variable not set."""
    mock_shell_utils.run_command.return_value = ("", "", 0)
    with pytest.raises(systemctl_utils.NoSystemdUserSessionError):
        assert not systemctl_utils.ensure_systemd_user_session()
    mock_shell_utils.run_command.assert_not_called()


@mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/run/user/1234"}, clear=True)
def test_invalid_systemd_user_session_systemctl_error(mock_shell_utils):
    """Test ensure_systemd_user_session - systemctl returned non-0 exit code."""
    mock_shell_utils.run_command.return_value = ("", "", 1)
    with pytest.raises(systemctl_utils.NoSystemdUserSessionError):
        assert not systemctl_utils.ensure_systemd_user_session()
    mock_shell_utils.run_command.assert_called_once_with(
        settings.SYSTEMCTL_USER_IS_SYSTEM_RUNNING_CMD
    )


def test_is_service_installed_when_installed(mock_shell_utils):
    """Test is_service_installed returns True when the service unit is present."""
    mock_shell_utils.run_command.return_value = ("", "", 0)
    assert systemctl_utils.is_service_installed() is True


def test_is_service_installed_when_not_installed(mock_shell_utils):
    """Test is_service_installed returns False when the service unit is not present."""
    mock_shell_utils.run_command.return_value = ("", "", 1)
    assert systemctl_utils.is_service_installed() is False


def test_check_service_running_when_active(mock_shell_utils):
    """Test check_service_running returns True when service is active."""
    mock_shell_utils.run_command.return_value = ("", "", 0)
    assert systemctl_utils.check_service_running() is True


def test_check_service_running_when_inactive(mock_shell_utils):
    """Test check_service_running returns False when service is not active."""
    mock_shell_utils.run_command.return_value = ("", "", 1)
    assert systemctl_utils.check_service_running() is False


def test_log_start_failure_details_prints_stdout(mock_shell_utils, capsys):
    """Test _log_start_failure_details prints status output when not quiet."""
    mock_shell_utils.run_command.return_value = ("service status output", "", 1)
    with mock.patch.object(systemctl_utils.settings, "runtime") as mock_runtime:
        mock_runtime.quiet = False
        systemctl_utils._log_start_failure_details()

    captured = capsys.readouterr()
    assert "service status output" in captured.out


def test_log_start_failure_details_quiet_suppresses_stdout(mock_shell_utils, capsys):
    """Test _log_start_failure_details skips printing status output in quiet mode."""
    mock_shell_utils.run_command.return_value = ("service status output", "", 1)
    with mock.patch.object(systemctl_utils.settings, "runtime") as mock_runtime:
        mock_runtime.quiet = True
        systemctl_utils._log_start_failure_details()

    captured = capsys.readouterr()
    assert captured.out == ""


def test_start_service_happy_path(mock_shell_utils):
    """Test start_service returns True when service becomes active quickly."""
    mock_shell_utils.run_command.side_effect = [
        ("", "", 0),  # systemctl reset-failed
        ("", "", 0),  # systemctl start network
        ("", "", 0),  # systemctl start app
    ]

    with mock.patch.object(systemctl_utils, "check_service_running", return_value=True):
        assert systemctl_utils.start_service()


def test_start_service_polls_until_active(mock_shell_utils):
    """Test start_service polls and succeeds after a few iterations."""
    # start succeeds; is-failed returns 1 (not failed) for each wait iteration;
    # on the 3rd check_service_running call, the service is active and we stop.
    mock_shell_utils.run_command.side_effect = [
        ("", "", 0),  # systemctl reset-failed
        ("", "", 0),  # systemctl start network
        ("", "", 0),  # systemctl start app
        ("", "", 1),  # is-failed: exit 1 = service is NOT failed (still starting)
        ("", "", 1),  # is-failed: exit 1 = service is NOT failed (still starting)
        # 3rd check_service_running returns True, so is-failed is never called again
    ]

    call_count = 0

    def check_running_side_effect():
        nonlocal call_count
        call_count += 1
        return call_count >= 3  # active on the 3rd poll

    with (
        mock.patch.object(
            systemctl_utils,
            "check_service_running",
            side_effect=check_running_side_effect,
        ),
        mock.patch.object(systemctl_utils, "time") as mock_time,
    ):
        # monotonic returns values that won't expire the deadline
        mock_time.monotonic.side_effect = [0, 0, 10, 20, 30, 40, 50]
        assert systemctl_utils.start_service()

    assert call_count == 3


def test_start_service_fails_on_failed_state(mock_shell_utils):
    """Test start_service returns False when service enters failed state."""
    mock_shell_utils.run_command.side_effect = [
        ("", "", 0),  # systemctl start
        ("status output", "", 1),  # status (called in _log_start_failure_details)
    ]

    with (
        mock.patch.object(systemctl_utils, "check_service_running", return_value=False),
        mock.patch.object(systemctl_utils, "_log_start_failure_details") as mock_log,
        mock.patch.object(systemctl_utils, "time") as mock_time,
    ):
        mock_time.monotonic.side_effect = [0, 0, 10]
        # is-failed returns 0 (service IS failed)
        mock_shell_utils.run_command.side_effect = [
            ("", "", 0),  # systemctl reset-failed
            ("", "", 0),  # systemctl start network
            ("", "", 0),  # systemctl start app
            ("", "", 0),  # is-failed → failed (exit 0 means IS failed)
        ]

        assert not systemctl_utils.start_service()
        mock_log.assert_called_once()


def test_start_service_fails_when_start_command_raises(mock_shell_utils):
    """Test start_service returns False when systemctl start command itself fails."""
    mock_shell_utils.run_command.side_effect = subprocess.CalledProcessError(
        1, settings.SYSTEMCTL_USER_START_QUIPUCORDS_APP
    )

    with mock.patch.object(systemctl_utils, "_log_start_failure_details") as mock_log:
        assert not systemctl_utils.start_service()
        mock_log.assert_called_once()


def test_start_service_timeout(mock_shell_utils):
    """Test start_service returns False when timeout is exceeded."""
    mock_shell_utils.run_command.return_value = ("", "", 0)

    with (
        mock.patch.object(systemctl_utils, "check_service_running", return_value=False),
        mock.patch.object(systemctl_utils, "_log_start_failure_details") as mock_log,
        mock.patch.object(systemctl_utils, "time") as mock_time,
    ):
        # is-failed returns 1 (not failed yet), but deadline expires immediately
        mock_shell_utils.run_command.side_effect = [
            ("", "", 0),  # systemctl reset-failed
            ("", "", 0),  # systemctl start network
            ("", "", 0),  # systemctl start app
        ]
        # First monotonic call sets deadline, second is already past it
        mock_time.monotonic.side_effect = [0, 999]

        assert not systemctl_utils.start_service()
        mock_log.assert_called_once()
