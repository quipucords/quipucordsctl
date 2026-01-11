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
    expected_log_message = "The admin login username was not updated."

    assert not reset_admin_username.run(argparse.Namespace())
    assert expected_log_message in caplog.messages


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


@mock.patch.object(reset_admin_username.secrets, "build_similar_value_check")
@mock.patch.object(reset_admin_username.secrets, "reset_username")
def test_reset_admin_username_builds_similarity_check_when_password_exists(
    mock_reset_username, mock_build_check
):
    """Test run() builds similarity check when password secret exists."""
    mock_similar_check = mock.Mock()
    mock_build_check.return_value = mock_similar_check
    mock_reset_username.return_value = True

    reset_admin_username.run(argparse.Namespace())

    mock_build_check.assert_called_once_with(
        secret_name=reset_admin_username.PASSWORD_SECRET_NAME,
        display_name="admin login password",
    )

    call_kwargs = mock_reset_username.call_args.kwargs
    assert call_kwargs["check_requirements"]["check_similar"] == mock_similar_check


@mock.patch.object(reset_admin_username.secrets, "build_similar_value_check")
@mock.patch.object(reset_admin_username.secrets, "reset_username")
def test_reset_admin_username_skips_similarity_check_when_password_not_exists(
    mock_reset_username, mock_build_check
):
    """Test run() skips similarity check when password secret doesn't exist."""
    mock_build_check.return_value = None
    mock_reset_username.return_value = True

    reset_admin_username.run(argparse.Namespace())

    call_kwargs = mock_reset_username.call_args.kwargs
    assert "check_similar" not in call_kwargs["check_requirements"]


@mock.patch.object(reset_admin_username.secrets, "build_similar_value_check")
@mock.patch.object(reset_admin_username.secrets, "reset_username")
def test_reset_admin_username_disables_password_validations(
    mock_reset_username, mock_build_check
):
    """Test run() disables password-style validations for usernames."""
    mock_build_check.return_value = None
    mock_reset_username.return_value = True

    reset_admin_username.run(argparse.Namespace())

    call_kwargs = mock_reset_username.call_args.kwargs
    reqs = call_kwargs["check_requirements"]

    assert reqs["min_length"] == 1
    assert reqs["digits"] is False
    assert reqs["letters"] is False
    assert reqs["not_isdigit"] is False


def test_reset_admin_username_rejects_similar_to_password(
    mock_first_time_run, mocker, caplog
):
    """Test username is rejected when too similar to existing password."""
    mock_first_time_run(reset_admin_username)

    mocker.patch.object(
        reset_admin_username.secrets.podman_utils,
        "get_secret_value",
        return_value="secretpass",
    )
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value="secretpass",
    )

    caplog.set_level(logging.ERROR)
    result = reset_admin_username.run(argparse.Namespace())

    assert not result
    assert "too similar" in caplog.text.lower()


def test_reset_admin_username_accepts_different_from_password(
    mock_first_time_run, mocker, caplog
):
    """Test username is accepted when sufficiently different from password."""
    mock_first_time_run(reset_admin_username)

    mocker.patch.object(
        reset_admin_username.secrets.podman_utils,
        "get_secret_value",
        return_value="Xk9#mP2$vL5@",
    )
    mocker.patch.object(
        reset_admin_username.secrets,
        "prompt_username",
        return_value="shadowman",
    )
    mocker.patch.object(
        reset_admin_username.podman_utils,
        "set_secret",
        return_value=True,
    )

    caplog.set_level(logging.DEBUG)
    result = reset_admin_username.run(argparse.Namespace())

    assert result
