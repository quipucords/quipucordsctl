"""Test the shell_utils module."""

import subprocess
from unittest import mock

import pytest

from quipucordsctl import shell_utils


@pytest.mark.parametrize(
    "user_inputs,expected",
    (
        (["y"], True),
        (["n"], False),
        (["Y"], True),
        (["N"], False),
        (["no", "what", "yes", "", " ", "\t", "Y"], True),
        (["hello", "world", "YES", "N"], False),
    ),
)
@mock.patch("builtins.input")
def test_confirm(mock_input, user_inputs, expected, capsys):
    """Test confirm handles various inputs."""
    mock_input.side_effect = user_inputs
    assert shell_utils.confirm() is expected
    assert mock_input.call_count == len(user_inputs)
    mock_input.assert_called_with("Do you want to continue? [y/n] ")
    if len(user_inputs) > 1:
        stdout = capsys.readouterr().out
        assert "Please answer with 'y' or 'n'." in stdout
        assert len(stdout.splitlines()) == len(user_inputs) - 1


@pytest.mark.parametrize(
    "yes, quiet, expect_input, expected_result",
    (
        # yes/quiet combos that expect input
        (None, None, True, True),
        (False, None, True, True),
        (None, False, True, True),
        (False, False, True, True),
        # yes/quiet combos that expect NO input
        (True, None, False, True),
        (None, True, False, False),
        (True, False, False, True),
        (False, True, False, False),
        (True, True, False, True),
    ),
)
@mock.patch("builtins.input")
@mock.patch.object(shell_utils.settings, "runtime")
def test_confirm_skipped_via_args(  # noqa: PLR0913
    mock_runtime, mock_input, yes, quiet, expect_input, expected_result, faker, capsys
):
    """Test confirm handles various "yes" and "quiet" settings."""
    mock_runtime.yes = yes
    mock_runtime.quiet = quiet
    mock_input.return_value = "y"
    prompt = faker.sentence()

    result = shell_utils.confirm(prompt)

    if yes or quiet:
        assert result is expected_result
        assert mock_input.call_count == 0
    else:
        assert mock_input.call_count == 1
        mock_input.assert_called_once_with(prompt)


@mock.patch("builtins.input")
def test_confirm_custom_prompt(mock_input, faker):
    """Test confirm can use a custom prompt."""
    mock_input.return_value = "y"
    prompt = faker.sentence()
    assert shell_utils.confirm(prompt)
    assert mock_input.call_count == 1
    mock_input.assert_called_once_with(prompt)


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
