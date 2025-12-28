"""Test the "reset_admin_password" command."""

import argparse
import logging
from unittest import mock

from quipucordsctl.commands import reset_admin_password
from tests.conftest import assert_reset_command_help


def test_get_help():
    """Test the get_help and get_description return appropriate strings."""
    assert_reset_command_help(reset_admin_password, "admin login password")


@mock.patch.object(reset_admin_password.podman_utils, "secret_exists")
def test_admin_password_is_set(mock_secret_exists):
    """Test is_set just wraps secret_exists."""
    assert reset_admin_password.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(reset_admin_password.PODMAN_SECRET_NAME)


def test_reset_admin_password_run_success(
    mock_first_time_run, good_secret, mocker, caplog
):
    """Test reset_admin_password.run succeeds in the default happy path."""
    mock_first_time_run(reset_admin_password)
    mocker.patch.object(
        reset_admin_password.secrets,
        "prompt_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_admin_password.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    assert reset_admin_password.run(argparse.Namespace())
    assert "The admin login password was successfully updated." == caplog.messages[-1]


def test_reset_admin_password_run_uses_env_var(good_secret, mocker, caplog):
    """Test reset_admin_password.run successfully uses its environment variable."""
    mocker.patch.object(
        reset_admin_password.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_admin_password.secrets.shell_utils,
        "get_env",
        return_value=good_secret,
    )
    set_secret = mocker.patch.object(
        reset_admin_password.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    assert reset_admin_password.run(argparse.Namespace())
    assert "The admin login password was successfully updated." == caplog.messages[-1]
    set_secret.assert_called_once_with(
        reset_admin_password.PODMAN_SECRET_NAME, good_secret, False
    )


def test_reset_admin_password_run_unexpected_failure(
    mock_first_time_run, good_secret, mocker, caplog
):
    """Test reset_admin_password.run when set_secret fails unexpectedly."""
    mock_first_time_run(reset_admin_password)
    mocker.patch.object(
        reset_admin_password.secrets,
        "prompt_secret",
        return_value=good_secret,
    )
    mocker.patch.object(
        reset_admin_password.podman_utils,
        "set_secret",
        return_value=False,
    )

    caplog.set_level(logging.ERROR)
    expected_last_log_message = "The admin login password was not updated."

    assert not reset_admin_password.run(argparse.Namespace())
    assert expected_last_log_message == caplog.messages[0]
