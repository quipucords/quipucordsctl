"""Test the systemctl_utils module."""

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
