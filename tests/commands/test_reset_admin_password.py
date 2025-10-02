"""Test the "reset_admin_password" command."""

import argparse
import logging
from unittest import mock

import pytest

from quipucordsctl.commands import reset_admin_password


class MysteryError(Exception):
    """Something completely unexpected happened."""

    def __str__(self):
        """Get string representation."""
        return self.__doc__


@mock.patch.object(reset_admin_password.podman_utils, "secret_exists")
def test_admin_password_is_set(mock_secret_exists):
    """Test admin_password_is_set just wraps secret_exists."""
    assert reset_admin_password.is_set() == mock_secret_exists.return_value
    mock_secret_exists.assert_called_once_with(
        reset_admin_password.ADMIN_PASSWORD_PODMAN_SECRET_NAME
    )


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
@mock.patch.object(reset_admin_password.secrets, "read_from_env")
def test_reset_admin_password_run_success(
    mock_read_from_env, mock_prompt_secret, mock_set_secret, good_secret, caplog
):
    """Test reset_admin_password.run is successful."""
    caplog.set_level(logging.ERROR)
    args = argparse.Namespace()
    mock_read_from_env.return_value = None, False
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.return_value = True
    assert reset_admin_password.run(args)
    mock_read_from_env.assert_called_once()
    assert len(caplog.messages) == 0


@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
@mock.patch.object(reset_admin_password.secrets, "read_from_env")
def test_reset_admin_password_run_bad_password(mock_read_from_env, mock_prompt_secret):
    """Test reset_admin_password.run when password fails validation checks."""
    args = argparse.Namespace()
    mock_read_from_env.return_value = None, False
    mock_prompt_secret.return_value = None
    assert not reset_admin_password.run(args)


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
@mock.patch.object(reset_admin_password.secrets, "read_from_env")
def test_reset_admin_password_run_podman_unexpected_failure(
    mock_read_from_env, mock_prompt_secret, mock_set_secret, good_secret, caplog
):
    """Test reset_admin_password.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    args = argparse.Namespace()
    mock_read_from_env.return_value = None, False
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.return_value = False
    assert not reset_admin_password.run(args)
    assert "The admin login password was not updated." == caplog.messages[0]


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
@mock.patch.object(reset_admin_password.secrets, "read_from_env")
def test_reset_admin_password_run_podman_unexpected_exception(
    mock_read_from_env, mock_prompt_secret, mock_set_secret, good_secret
):
    """Test reset_admin_password.run when a truly unexpected error occurs."""
    args = argparse.Namespace()
    mock_read_from_env.return_value = None, False
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.side_effect = MysteryError
    with pytest.raises(MysteryError):
        # OK to raise here because main.main handles exceptions.
        reset_admin_password.run(args)


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
@mock.patch.object(reset_admin_password.secrets, "read_from_env")
def test_reset_admin_password_run_headless_mode(
    mock_read_from_env,
    mock_prompt_secret,
    mock_set_secret,
    good_secret,
    caplog,
):
    """Test reset_admin_password.run using env vars."""
    caplog.set_level(logging.ERROR)
    args = argparse.Namespace()
    mock_read_from_env.return_value = good_secret, False
    mock_set_secret.return_value = True
    assert reset_admin_password.run(args)
    mock_prompt_secret.assert_not_called()
    mock_read_from_env.assert_called_once()
    assert len(caplog.messages) == 0
