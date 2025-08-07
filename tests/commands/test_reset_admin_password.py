"""Test the "reset_admin_password" command."""

import logging
import uuid
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


@mock.patch.object(reset_admin_password.shell_utils, "get_podman_client")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_success(mock_prompt_secret, mock_popen, caplog):
    """Test reset_admin_password.run is successful."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    mock_process = mock_popen.return_value  # act like oc process succeeded
    mock_process.communicate.return_value = (None, None)
    mock_process.returncode = 0
    assert reset_admin_password.run(mock_args)
    assert len(caplog.messages) == 0


@mock.patch.object(reset_admin_password.shell_utils, "get_podman_client")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_success_verbose_verbose(
    mock_prompt_secret, mock_get_podman_client, caplog, faker
):
    """Test reset_admin_password.run logs details with 2 --verbose flags."""
    caplog.set_level(logging.DEBUG)
    mock_args = mock.Mock()
    mock_args.verbosity = 2
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password

    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert reset_admin_password.run(mock_args)
    assert (
        f"A podman secret {reset_admin_password.PODMAN_SECRET_NAME} already exists."
        == caplog.messages[0]
    )
    assert (
        f"Old podman secret {reset_admin_password.PODMAN_SECRET_NAME} was removed."
        == caplog.messages[1]
    )
    assert (
        f"New podman secret {reset_admin_password.PODMAN_SECRET_NAME} was set."
        == caplog.messages[2]
    )


@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_bad_password(mock_prompt_secret):
    """Test reset_admin_password.run when password fails validation checks."""
    mock_args = mock.Mock()
    mock_prompt_secret.return_value = None
    assert not reset_admin_password.run(mock_args)


@mock.patch.object(reset_admin_password.shell_utils, "get_podman_client")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_podman_unexpected_error(
    mock_prompt_secret, mock_get_podman_client
):
    """Test reset_admin_password.run when a truly unexpected error occurs."""
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True
    mock_podman_client.secrets.create.side_effect = MysteryError
    with pytest.raises(MysteryError):
        # OK to raise here because main.main handles exceptions.
        reset_admin_password.run(mock_args)
    mock_podman_client.secrets.exists.assert_called_once_with(
        reset_admin_password.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.remove.assert_called_once_with(
        reset_admin_password.PODMAN_SECRET_NAME
    )
    mock_podman_client.secrets.create.assert_called_once_with(
        reset_admin_password.PODMAN_SECRET_NAME, password
    )
