"""Test the shell_utils module."""

import subprocess
from unittest import mock

import pytest

from quipucordsctl import shell_utils


def test_run_command():
    """Test happy path of run_command."""
    example_command = ["echo", "hello"]
    with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
        mock_popen = mock_subprocess.Popen.return_value
        mock_popen.communicate.return_value = ("stdout", "stderr")
        mock_popen.returncode = 0
        shell_utils.run_command(example_command)
    mock_subprocess.Popen.assert_called_once_with(
        args=example_command,
        stdout=mock_subprocess.PIPE,
        stderr=mock_subprocess.PIPE,
        text=True,
    )
    mock_subprocess.Popen.return_value.communicate.assert_called_once()


def test_run_command_error():
    """Test failure (nonzero return code) of run_command."""
    example_command = ["echo", "hello"]
    with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
        mock_popen = mock_subprocess.Popen.return_value
        mock_popen.communicate.return_value = ("stdout", "stderr")
        mock_popen.returncode = 1
        mock_subprocess.CalledProcessError = subprocess.CalledProcessError
        with pytest.raises(subprocess.CalledProcessError):
            shell_utils.run_command(example_command)
