"""Test the shell_utils module."""

import logging
import pathlib
import subprocess
from unittest import mock

import pytest

from quipucordsctl import settings, shell_utils


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
        mock_input.assert_called_once_with(f"{prompt} [y/n] ")


@mock.patch("builtins.input")
def test_confirm_custom_prompt(mock_input, faker):
    """Test confirm can use a custom prompt."""
    mock_input.return_value = "y"
    prompt = faker.sentence()
    assert shell_utils.confirm(prompt)
    assert mock_input.call_count == 1
    mock_input.assert_called_once_with(f"{prompt} [y/n] ")


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
        stdin=mock_subprocess.DEVNULL,
        stdout=mock_subprocess.PIPE,
        stderr=mock_subprocess.PIPE,
        text=True,
        shell=False,
        env=None,
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


def test_template_dir():
    """Test that template_dir for RPM-based installations is off /usr/share."""
    with mock.patch("quipucordsctl.shell_utils.is_rpm_exec") as mock_is_rpm_exec:
        mock_is_rpm_exec.return_value = True
        assert shell_utils.template_dir() == pathlib.Path(
            f"/usr/share/{settings.PROGRAM_NAME}"
        )


def test_run_command_logs_stdout_on_success(caplog):
    """Test stdout is logged at DEBUG level when command succeeds."""
    with caplog.at_level(logging.DEBUG):
        with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
            mock_popen = mock_subprocess.Popen.return_value
            mock_popen.communicate.return_value = ("line1\nline2", "")
            mock_popen.returncode = 0
            mock_subprocess.PIPE = subprocess.PIPE

            shell_utils.run_command(["echo", "test"])

    assert "line1" in caplog.text
    assert "line2" in caplog.text


def test_run_command_logs_stderr_on_failure(caplog):
    """Test stderr is logged at ERROR level when command fails."""
    with caplog.at_level(logging.DEBUG):
        with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
            mock_popen = mock_subprocess.Popen.return_value
            mock_popen.communicate.return_value = ("", "error line1\nerror line2")
            mock_popen.returncode = 1
            mock_subprocess.PIPE = subprocess.PIPE
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError

            with pytest.raises(subprocess.CalledProcessError):
                shell_utils.run_command(["failing", "cmd"])

    assert "error line1" in caplog.text
    assert "error line2" in caplog.text


def test_run_command_with_stdin():
    """Test run_command passes stdin to subprocess."""
    with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
        mock_popen = mock_subprocess.Popen.return_value
        mock_popen.communicate.return_value = ("output", "")
        mock_popen.returncode = 0
        mock_subprocess.PIPE = subprocess.PIPE

        shell_utils.run_command(["cat"], stdin="input data")

    mock_subprocess.Popen.assert_called_once()
    call_kwargs = mock_subprocess.Popen.call_args[1]
    assert call_kwargs["stdin"] == subprocess.PIPE
    mock_popen.communicate.assert_called_once_with(input="input data", timeout=mock.ANY)


def test_run_command_redact_output_hides_stdout(caplog):
    """Test redact_output=True hides actual stdout content."""
    with caplog.at_level(logging.DEBUG):
        with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
            mock_popen = mock_subprocess.Popen.return_value
            mock_popen.communicate.return_value = ("secret_password_123", "")
            mock_popen.returncode = 0
            mock_subprocess.PIPE = subprocess.PIPE

            shell_utils.run_command(["echo", "secret"], redact_output=True)

    assert "secret_password_123" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_run_command_redact_output_hides_stderr(caplog):
    """Test redact_output=True hides actual stderr content."""
    with caplog.at_level(logging.DEBUG):
        with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
            mock_popen = mock_subprocess.Popen.return_value
            mock_popen.communicate.return_value = ("", "secret_error_info")
            mock_popen.returncode = 1
            mock_subprocess.PIPE = subprocess.PIPE
            mock_subprocess.CalledProcessError = subprocess.CalledProcessError

            with pytest.raises(subprocess.CalledProcessError):
                shell_utils.run_command(["cmd"], redact_output=True)

    assert "secret_error_info" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_run_command_raise_error_false_allows_failure():
    """Test run_command with raise_error=False returns exit code without raising."""
    with mock.patch("quipucordsctl.shell_utils.subprocess") as mock_subprocess:
        mock_popen = mock_subprocess.Popen.return_value
        mock_popen.communicate.return_value = ("", "error")
        mock_popen.returncode = 42
        mock_subprocess.PIPE = subprocess.PIPE

        stdout, stderr, exit_code = shell_utils.run_command(
            ["failing", "cmd"], raise_error=False
        )

    assert exit_code == 42
    assert stderr == "error"
