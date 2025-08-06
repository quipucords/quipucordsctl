"""Test the "reset_admin_password" command."""

import logging
import uuid
from unittest import mock

from quipucordsctl.commands import reset_admin_password


class MysteryError(Exception):
    """Something completely unexpected happened."""

    def __str__(self):
        """Get string representation."""
        return self.__doc__


def test_admin_password_is_set():
    """Test placeholder for admin_password_is_set."""
    assert not reset_admin_password.admin_password_is_set()


@mock.patch.object(reset_admin_password.subprocess, "Popen")
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


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_success_verbose_verbose(
    mock_prompt_secret, mock_popen, caplog, faker
):
    """Test reset_admin_password.run logs details with 2 --verbose flags."""
    caplog.set_level(logging.DEBUG)
    mock_args = mock.Mock()
    mock_args.verbosity = 2
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    process_stdout = faker.sentence()  # act like oc process succeeded
    mock_process = mock_popen.return_value
    mock_process.communicate.return_value = (process_stdout, None)
    mock_process.returncode = 0
    assert reset_admin_password.run(mock_args)
    assert "created/replaced successfully" in caplog.messages[0]
    assert "stdout" in caplog.messages[1]
    assert process_stdout in caplog.messages[2]


@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_bad_password(mock_prompt_secret):
    """Test reset_admin_password.run when password fails validation checks."""
    mock_args = mock.Mock()
    mock_prompt_secret.return_value = None
    assert not reset_admin_password.run(mock_args)


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_oc_fails(mock_prompt_secret, mock_popen, caplog):
    """Test reset_admin_password.run when the `oc` command fails."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    mock_process = mock_popen.return_value  # act like oc process failed
    mock_process.communicate.return_value = (None, None)
    mock_process.returncode = 1
    assert not reset_admin_password.run(mock_args)
    assert "Failed to create podman secret" in caplog.messages[0]


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_oc_not_installed(
    mock_prompt_secret, mock_popen, caplog
):
    """Test reset_admin_password.run when the `oc` program is not found in the PATH."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    mock_process = mock_popen.return_value  # act like oc program could not be found
    mock_process.communicate.side_effect = FileNotFoundError
    assert not reset_admin_password.run(mock_args)
    assert "command not found" in caplog.messages[0]


@mock.patch.object(reset_admin_password.subprocess, "Popen")
@mock.patch.object(reset_admin_password.secrets, "prompt_secret")
def test_reset_admin_password_run_truly_unexpected_error(
    mock_prompt_secret, mock_popen, caplog
):
    """Test reset_admin_password.run when a truly unexpected error occurs."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()
    mock_args.verbosity = 0
    password = str(uuid.uuid4())
    mock_prompt_secret.return_value = password
    mock_process = mock_popen.return_value
    mock_process.communicate.side_effect = MysteryError
    assert not reset_admin_password.run(mock_args)
    assert "An unexpected error occurred" in caplog.messages[0]
    assert MysteryError.__doc__ in caplog.messages[0]
