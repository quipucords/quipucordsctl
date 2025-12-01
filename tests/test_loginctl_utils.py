"""Test the loginctl_utils module."""

import logging
import subprocess
from unittest import mock

from quipucordsctl import loginctl_utils


def test_is_linger_enabled_yes(faker):
    """Test returns True if Linger is enabled for a user."""
    with (
        mock.patch.object(
            loginctl_utils.shell_utils, "run_command"
        ) as mock_run_command,
    ):
        username = faker.user_name()
        mock_run_command.return_value = ["Linger=yes", "", 0]
        return_value = loginctl_utils.is_linger_enabled(username)
        mock_run_command.assert_called_once_with(
            ["loginctl", "show-user", username, "--property=Linger"],
            env=mock.ANY,
        )
        assert return_value


def test_is_linger_enabled_no(faker):
    """Test returns False if Linger is not enabled for a user."""
    with (
        mock.patch.object(
            loginctl_utils.shell_utils, "run_command"
        ) as mock_run_command,
    ):
        username = faker.user_name()
        mock_run_command.return_value = ["Linger=no", "", 0]
        return_value = loginctl_utils.is_linger_enabled(username)
        mock_run_command.assert_called_once_with(
            ["loginctl", "show-user", username, "--property=Linger"],
            env=mock.ANY,
        )
        assert not return_value


def test_is_linger_enabled_loginctl_fails(faker):
    """Test returns False if loginctl command fails is not enabled for a user."""
    with (
        mock.patch.object(
            loginctl_utils.shell_utils, "run_command"
        ) as mock_run_command,
    ):
        username = faker.user_name()
        mock_run_command.return_value = ["", "error message", 1]
        return_value = loginctl_utils.is_linger_enabled(username)
        mock_run_command.assert_called_once_with(
            ["loginctl", "show-user", username, "--property=Linger"],
            env=mock.ANY,
        )
        assert not return_value


def test_check_linger_logs_message_if_enabled(faker, caplog):
    """Test method logs message if Linger is enabled for the current user."""
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
        mock.patch.object(
            loginctl_utils, "is_linger_enabled"
        ) as mock_is_linger_enabled,
    ):
        caplog.set_level(logging.INFO)
        username = faker.user_name()
        mock_getuser.return_value = username
        mock_is_linger_enabled.return_value = True
        return_value = loginctl_utils.check_linger()

        mock_is_linger_enabled.assert_called_once_with(username)
        message = f"Linger is enabled for user '{username}'"
        assert message in caplog.messages
        assert return_value


def test_check_linger_returns_failure_if_is_linger_enabled_errors(faker, caplog):
    """Test method logs error if is_linger_enables raises an exception."""
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
        mock.patch.object(
            loginctl_utils, "is_linger_enabled"
        ) as mock_is_linger_enabled,
    ):
        caplog.set_level(logging.INFO)
        username = faker.user_name()
        mock_getuser.return_value = username
        mock_is_linger_enabled.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="/bin/false"
        )
        return_value = loginctl_utils.check_linger()

        mock_is_linger_enabled.assert_called_once_with(username)
        assert f"Linger is enabled for user '{username}'" not in caplog.messages[0]
        assert "loginctl failed unexpectedly" in caplog.messages[0]
        assert not return_value


def test_enable_linger_with_nolinger(faker, caplog):
    """Test method does not enable linger if no_linger is specified."""
    username = faker.user_name()
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
    ):
        caplog.set_level(logging.INFO)
        mock_getuser.return_value = username
        return_value = loginctl_utils.enable_linger(False)
        message = f"Linger will not be enabled for user '{username}'"
        assert message in caplog.messages[0]
        assert return_value


def test_enable_linger_already_enabled(faker, caplog):
    """Test method does not enable linger if already enabled."""
    username = faker.user_name()
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
        mock.patch.object(
            loginctl_utils, "is_linger_enabled"
        ) as mock_is_linger_enabled,
    ):
        caplog.set_level(logging.INFO)
        mock_getuser.return_value = username
        mock_is_linger_enabled.return_value = True
        return_value = loginctl_utils.enable_linger(True)
        message = f"Linger is enabled for user '{username}'"
        assert message in caplog.messages[0]
        assert return_value


def test_enable_linger(faker, caplog):
    """Test method enables linger."""
    username = faker.user_name()
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
        mock.patch.object(
            loginctl_utils, "is_linger_enabled"
        ) as mock_is_linger_enabled,
        mock.patch.object(
            loginctl_utils.shell_utils, "run_command"
        ) as mock_run_command,
    ):
        caplog.set_level(logging.INFO)
        mock_getuser.return_value = username
        mock_is_linger_enabled.return_value = False
        return_value = loginctl_utils.enable_linger(True)
        mock_run_command.assert_called_once_with(
            [
                "loginctl",
                "enable-linger",
                username,
            ]
        )
        message = f"Enabling Linger for user '{username}'"
        assert message in caplog.messages[0]
        assert return_value


def test_enable_linger_returns_false_if_loginctl_raises_exception(faker, caplog):
    """Test method returns False if loginctl raises an exception."""
    username = faker.user_name()
    with (
        mock.patch.object(loginctl_utils.getpass, "getuser") as mock_getuser,
        mock.patch.object(
            loginctl_utils, "is_linger_enabled"
        ) as mock_is_linger_enabled,
        mock.patch.object(
            loginctl_utils.shell_utils, "run_command"
        ) as mock_run_command,
    ):
        caplog.set_level(logging.INFO)
        mock_getuser.return_value = username
        mock_is_linger_enabled.return_value = False
        mock_run_command.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="/bin/false"
        )
        return_value = loginctl_utils.enable_linger(True)
        mock_run_command.assert_called_once_with(
            [
                "loginctl",
                "enable-linger",
                username,
            ]
        )
        message = (
            "loginctl failed unexpectedly,"
            f" unable to enable Linger for user '{username}'"
        )
        assert message in caplog.messages[-1]
        assert not return_value
