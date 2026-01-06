"""Test the "reset_admin_password" command."""

import argparse
import logging
from unittest import mock

import pytest

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


@mock.patch.object(reset_admin_password.secrets, "build_similar_value_check")
@mock.patch.object(reset_admin_password.secrets, "reset_secret")
def test_reset_admin_password_builds_similarity_check_when_username_exists(
    mock_reset_secret, mock_build_check, faker
):
    """Test run() builds similarity check when username secret exists."""
    mock_similar_check = mock.Mock()
    mock_build_check.return_value = mock_similar_check
    mock_reset_secret.return_value = True

    reset_admin_password.run(argparse.Namespace())

    mock_build_check.assert_called_once_with(
        secret_name=reset_admin_password.USERNAME_SECRET_NAME,
        display_name="admin login username",
    )

    call_kwargs = mock_reset_secret.call_args.kwargs
    assert call_kwargs["check_requirements"]["check_similar"] == mock_similar_check


@mock.patch.object(reset_admin_password.secrets, "build_similar_value_check")
@mock.patch.object(reset_admin_password.secrets, "reset_secret")
def test_reset_admin_password_skips_similarity_check_when_username_not_exists(
    mock_reset_secret, mock_build_check
):
    """Test run() skips similarity check when username secret doesn't exist."""
    mock_build_check.return_value = None
    mock_reset_secret.return_value = True

    reset_admin_password.run(argparse.Namespace())

    call_kwargs = mock_reset_secret.call_args.kwargs
    assert "check_similar" not in call_kwargs["check_requirements"]


@pytest.mark.parametrize(
    "username,password",
    [
        ("shadowman", "shadowman1"),
        ("shadowman", "1shadowman"),
        ("shadowman", "xshadowmanx"),
        ("shadowman99", "shadowman1"),
        ("shadowman", "shadowmen1"),
        ("shadowman", "shadowXman"),
        ("shadowman", "shadoman12"),
        ("shadowman", "namwodahs1"),
    ],
)
def test_reset_admin_password_rejects_similar_to_username(
    mock_first_time_run, mocker, caplog, username, password
):
    """Test password is rejected when too similar to existing username."""
    mock_first_time_run(reset_admin_password)

    mocker.patch.object(
        reset_admin_password.secrets.podman_utils,
        "get_secret_value",
        return_value=username,
    )
    mocker.patch.object(
        reset_admin_password.secrets,
        "prompt_secret",
        return_value=password,
    )

    caplog.set_level(logging.ERROR)
    result = reset_admin_password.run(argparse.Namespace())

    assert not result
    assert "too similar" in caplog.text.lower()


@pytest.mark.parametrize(
    "username,password",
    [
        ("shadowman", "Xk9#mP2$vL"),
        ("shadowman", "shadow1234"),
        ("shadowman", "shad123456"),
        ("shadowman", "12shadow34"),
    ],
)
def test_reset_admin_password_accepts_different_from_username(
    mock_first_time_run, mocker, caplog, username, password
):
    """Test password is accepted when sufficiently different from username."""
    mock_first_time_run(reset_admin_password)

    mocker.patch.object(
        reset_admin_password.secrets.podman_utils,
        "get_secret_value",
        return_value=username,
    )
    mocker.patch.object(
        reset_admin_password.secrets,
        "prompt_secret",
        return_value=password,
    )
    mocker.patch.object(
        reset_admin_password.podman_utils,
        "set_secret",
        return_value=True,
    )

    caplog.set_level(logging.DEBUG)
    result = reset_admin_password.run(argparse.Namespace())

    assert result
