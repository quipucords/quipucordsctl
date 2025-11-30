"""Test the "reset_admin_username" command."""

import argparse
import logging
from unittest import mock

from quipucordsctl.commands import reset_admin_username
from tests.conftest import assert_reset_command_help


def test_get_help():
    """Test the get_help and get_description return appropriate strings."""
    assert_reset_command_help(reset_admin_username, "admin login username")


@mock.patch.object(reset_admin_username.podman_utils, "secret_exists")
def test_admin_username_is_set(mock_secret_exists):
    """Test is_set just wraps secret_exists."""
    assert reset_admin_username.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(reset_admin_username.PODMAN_SECRET_NAME)


def test_reset_admin_username_run_success(mock_first_time_run, mocker, caplog):
    """Test reset_admin_username.run succeeds in the default happy path."""
    mock_first_time_run(reset_admin_username)
    test_username = "testuser"
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value=test_username,
    )
    mocker.patch.object(
        reset_admin_username.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    assert reset_admin_username.run(argparse.Namespace())
    assert "The admin login username was successfully updated." == caplog.messages[-1]


def test_reset_admin_username_run_uses_env_var(mocker, caplog):
    """Test reset_admin_username.run successfully uses its environment variable."""
    test_username = "envuser"
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "get_env",
        return_value=test_username,
    )
    set_secret = mocker.patch.object(
        reset_admin_username.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    assert reset_admin_username.run(argparse.Namespace())
    assert "The admin login username was successfully updated." == caplog.messages[-1]
    set_secret.assert_called_once_with(
        reset_admin_username.PODMAN_SECRET_NAME, test_username, False
    )


def test_reset_admin_username_run_unexpected_failure(
    mock_first_time_run, mocker, caplog
):
    """Test reset_admin_username.run when set_secret fails unexpectedly."""
    mock_first_time_run(reset_admin_username)
    test_username = "testuser"
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value=test_username,
    )
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "set_secret",
        return_value=False,
    )

    caplog.set_level(logging.ERROR)
    expected_last_log_message = "The admin login username was not updated."

    assert not reset_admin_username.run(argparse.Namespace())
    assert expected_last_log_message == caplog.messages[0]


def test_reset_admin_username_empty_username_fails(mock_first_time_run, mocker, caplog):
    """Test reset_admin_username.run fails when empty username is provided."""
    mock_first_time_run(reset_admin_username)
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value="   ",
    )

    caplog.set_level(logging.ERROR)
    assert not reset_admin_username.run(argparse.Namespace())
    assert "Username cannot be empty." == caplog.messages[0]


def test_reset_admin_username_requires_confirmation_when_replacing(mocker, caplog):
    """Test reset_admin_username.run requires confirmation when replacing existing."""
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=True,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "confirm",
        return_value=False,
    )

    caplog.set_level(logging.ERROR)
    expected_last_log_message = "The admin login username was not updated."

    assert not reset_admin_username.run(argparse.Namespace())
    assert expected_last_log_message == caplog.messages[0]


def test_reset_admin_username_succeeds_with_confirmation(mocker, caplog):
    """Test reset_admin_username.run succeeds when user confirms replacement."""
    test_username = "newuser"
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=True,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "confirm",
        return_value=True,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "get_env",
        return_value=None,
    )
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value=test_username,
    )
    mocker.patch.object(
        reset_admin_username.podman_utils, "set_secret", return_value=True
    )

    caplog.set_level(logging.DEBUG)
    assert reset_admin_username.run(argparse.Namespace())
    assert "The admin login username was successfully updated." == caplog.messages[-1]


def test_reset_admin_username_empty_env_var_fails(mocker, caplog):
    """Test reset_admin_username.run fails when env var has empty username."""
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "get_env",
        return_value="   ",  # empty/whitespace from env var
    )

    caplog.set_level(logging.ERROR)
    assert not reset_admin_username.run(argparse.Namespace())
    assert "Username cannot be empty." == caplog.messages[0]


def test_reset_admin_username_quiet_mode_fails(mocker, caplog):
    """Test reset_admin_username.run fails in quiet mode without env var."""
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "get_env",
        return_value=None,
    )
    mocker.patch.object(
        reset_admin_username.secrets.settings.runtime,
        "_quiet",
        True,
    )

    caplog.set_level(logging.ERROR)
    assert not reset_admin_username.run(argparse.Namespace())
    assert (
        "Username is required but cannot be prompted in quiet mode."
        == caplog.messages[0]
    )


def test_reset_admin_username_prompt_returns_none(mocker, caplog):
    """Test reset_admin_username.run fails when prompt returns None."""
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "secret_exists",
        return_value=False,
    )
    mocker.patch.object(
        reset_admin_username.secrets.shell_utils,
        "get_env",
        return_value=None,
    )
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value=None,  # prompt returns None
    )

    caplog.set_level(logging.ERROR)
    assert not reset_admin_username.run(argparse.Namespace())
    assert "Username cannot be empty." == caplog.messages[0]
    assert "The admin login username was not updated." == caplog.messages[1]
