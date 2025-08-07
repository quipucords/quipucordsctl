"""Test the "reset_admin_password" command."""

import logging
from unittest import mock

import pytest

from quipucordsctl.commands import reset_admin_password


class MysteryError(Exception):
    """Something completely unexpected happened."""

    def __str__(self):
        """Get string representation."""
        return self.__doc__


def test_admin_password_is_set():
    """Test placeholder for admin_password_is_set."""
    assert not reset_admin_password.admin_password_is_set()


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_success(
    mock_prompt_secret, mock_set_secret, good_secret, caplog
):
    """Test reset_admin_password.run is successful."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.return_value = True
    assert reset_admin_password.run(mock_args)
    assert len(caplog.messages) == 0


@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_bad_password(mock_prompt_secret):
    """Test reset_admin_password.run when password fails validation checks."""
    mock_args = mock.Mock()
    mock_prompt_secret.return_value = None
    assert not reset_admin_password.run(mock_args)


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_podman_unexpected_failure(
    mock_prompt_secret, mock_set_secret, good_secret, caplog
):
    """Test reset_admin_password.run when set_secret fails unexpectedly."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.return_value = False
    assert not reset_admin_password.run(mock_args)
    assert "The server login password was not updated." == caplog.messages[0]


@mock.patch.object(reset_admin_password.podman_utils, "set_secret")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_podman_unexpected_exception(
    mock_prompt_secret, mock_set_secret, good_secret
):
    """Test reset_admin_password.run when a truly unexpected error occurs."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    mock_prompt_secret.return_value = good_secret
    mock_set_secret.side_effect = MysteryError
    with pytest.raises(MysteryError):
        # OK to raise here because main.main handles exceptions.
        reset_admin_password.run(mock_args)
