"""Test the systemctl_utils module."""

import os
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
