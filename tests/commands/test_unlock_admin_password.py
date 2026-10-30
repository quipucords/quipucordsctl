"""Test the "unlock_admin_password" command."""

import argparse
import logging
import subprocess

import pytest

from quipucordsctl import argparse_utils, settings
from quipucordsctl.commands import unlock_admin_password

# Distinguishes "the test did not ask for a username" from an explicit None,
# which is what get_secret_value returns when the secret cannot be read.
UNSET = object()


@pytest.fixture
def mock_requirements(mocker):
    """Mock the systemd session and podman socket checks that run() performs."""
    return {
        "systemctl_utils": mocker.patch.object(
            unlock_admin_password, "systemctl_utils"
        ),
        "ensure_podman_socket": mocker.patch.object(
            unlock_admin_password.podman_utils, "ensure_podman_socket"
        ),
    }


@pytest.fixture
def mock_server(mocker, faker):
    """Mock the container interactions, defaulting to a running, cooperative server."""

    def _mock_server(*, is_running=True, exec_succeeds=True):
        return {
            "container_is_running": mocker.patch.object(
                unlock_admin_password.podman_utils,
                "container_is_running",
                return_value=is_running,
            ),
            "get_secret_value": mocker.patch.object(
                unlock_admin_password.podman_utils, "get_secret_value"
            ),
            "exec_in_container": mocker.patch.object(
                unlock_admin_password.podman_utils,
                "exec_in_container",
                return_value=exec_succeeds,
            ),
        }

    return _mock_server


def test_get_help():
    """Test get_help returns an appropriate string."""
    assert "Unlock" in unlock_admin_password.get_help()


def test_get_description():
    """Test get_description returns an appropriate string."""
    description = unlock_admin_password.get_description()
    assert settings.SERVER_SOFTWARE_NAME in description
    assert "`unlock_admin_password`" in description


def test_get_display_group():
    """Test get_display_group returns CONFIG."""
    assert (
        unlock_admin_password.get_display_group() == argparse_utils.DisplayGroups.CONFIG
    )


def test_unlock_admin_password_run_success(
    mock_requirements, mock_server, caplog, capsys
):
    """Test run clears the admin's lockout when the server container is running."""
    mocks = mock_server()

    caplog.set_level(logging.DEBUG)
    assert unlock_admin_password.run(argparse.Namespace())

    mocks["exec_in_container"].assert_called_once_with(
        settings.SERVER_CONTAINER_NAME,
        [
            "sh",
            "-c",
            settings.SERVER_AXES_RESET_ADMIN_SCRIPT,
            "sh",
            *settings.SERVER_AXES_RESET_USERNAME_COMMAND,
        ],
    )
    assert "The admin login lockout was successfully cleared." == caplog.messages[-1]
    assert "You may now try to log in again." in capsys.readouterr().out


def test_unlock_admin_password_run_fails_when_server_not_running(
    mock_requirements, mock_server, caplog
):
    """Test run returns False with guidance when the server is not running."""
    mocks = mock_server(is_running=False)

    caplog.set_level(logging.ERROR)
    assert not unlock_admin_password.run(argparse.Namespace())

    mocks["exec_in_container"].assert_not_called()
    assert f"{settings.PROGRAM_NAME} start" in caplog.text


def test_unlock_admin_password_run_fails_when_exec_fails(
    mock_requirements, mock_server, caplog
):
    """Test run returns False when the axes_reset command fails."""
    mock_server(exec_succeeds=False)

    caplog.set_level(logging.ERROR)
    assert not unlock_admin_password.run(argparse.Namespace())
    assert "Failed to clear the admin login lockout." == caplog.messages[-1]


def test_unlock_admin_password_never_reads_username_on_the_host(
    mock_requirements, mock_server
):
    """Test the username is resolved in the container, not from the host secret.

    Reading the podman secret here would append the newline that "podman secret
    inspect --format" adds, and would miss a secret changed after the server
    started, so axes would silently find no records and still report success.
    """
    mocks = mock_server()

    assert unlock_admin_password.run(argparse.Namespace())

    mocks["get_secret_value"].assert_not_called()
    command = mocks["exec_in_container"].call_args.args[1]
    assert settings.QUIPUCORDS_SECRETS["username"] not in command


def test_unlock_admin_password_run_checks_requirements_first(
    mock_requirements, mock_server
):
    """Test run ensures the systemd session and podman socket before proceeding."""
    mock_server()

    unlock_admin_password.run(argparse.Namespace())

    mock_requirements[
        "systemctl_utils"
    ].ensure_systemd_user_session.assert_called_once()
    mock_requirements["ensure_podman_socket"].assert_called_once()


def test_unlock_admin_password_quiet_mode_prints_nothing(
    mock_requirements, mock_server, capsys, monkeypatch
):
    """Test run does not print to stdout in quiet mode."""
    mock_server()
    monkeypatch.setattr(settings.runtime, "_quiet", True)

    assert unlock_admin_password.run(argparse.Namespace())
    assert capsys.readouterr().out == ""


def test_axes_reset_command_invokes_manage_py():
    """Test the configured command scopes the reset to a username via manage.py.

    The unqualified "axes_reset" would clear every account's and address's
    lockouts, so guard against it being reintroduced here.
    """
    assert settings.SERVER_AXES_RESET_USERNAME_COMMAND == [
        "python",
        "quipucords/manage.py",
        "axes_reset_username",
        "--settings",
        "quipucords.settings",
    ]
    assert "axes_reset" not in settings.SERVER_AXES_RESET_USERNAME_COMMAND


# conftest's autouse forbid_shell_utils_subprocess fixture blocks subprocess.Popen
# so product code cannot shell out during tests. The two tests below are not
# exercising product code; they run the reset script through a real "sh" to prove
# it handles the container's username correctly, so they restore the real Popen.
_REAL_POPEN = subprocess.Popen


@pytest.fixture
def allow_real_subprocess(monkeypatch):
    """Undo the autouse Popen guard for tests that must run a real shell."""
    monkeypatch.setattr("quipucordsctl.shell_utils.subprocess.Popen", _REAL_POPEN)


def _run_admin_script(username_env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run the admin reset script with "echo" standing in for the real command."""
    return subprocess.run(  # noqa: S603
        [
            "/bin/sh",  # absolute here; the container resolves "sh" from its PATH
            "-c",
            settings.SERVER_AXES_RESET_ADMIN_SCRIPT,
            "sh",
            "echo",
            "axes_reset_username",
        ],
        env=username_env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "username", ["admin", "-rf", "name with spaces", "admin\twith\ttabs"]
)
def test_admin_script_passes_container_username_after_dash_dash(
    username, allow_real_subprocess
):
    """Test the script forwards the container's username verbatim after "--"."""
    result = _run_admin_script({"QUIPUCORDS_SERVER_USERNAME": username})

    assert result.returncode == 0
    assert result.stdout == f"axes_reset_username -- {username}\n"


@pytest.mark.parametrize("env", [{}, {"QUIPUCORDS_SERVER_USERNAME": ""}])
def test_admin_script_fails_when_container_username_missing(env, allow_real_subprocess):
    """Test the script fails loudly rather than resetting an empty username.

    axes_reset_username exits 0 when it matches no records, so an empty value
    would be reported to the user as a successful unlock.
    """
    result = _run_admin_script(env)

    assert result.returncode != 0
    assert result.stdout == ""
