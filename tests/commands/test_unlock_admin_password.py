"""Test the "unlock_admin_password" command."""

import argparse
import logging

import pytest

from quipucordsctl import argparse_utils, settings
from quipucordsctl.commands import unlock_admin_password


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
def mock_server(mocker):
    """Mock the container interactions, defaulting to a running, cooperative server."""

    def _mock_server(*, is_running=True, exec_succeeds=True):
        return {
            "container_is_running": mocker.patch.object(
                unlock_admin_password.podman_utils,
                "container_is_running",
                return_value=is_running,
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
    """Test run clears the lockouts when the server container is running."""
    mocks = mock_server()

    caplog.set_level(logging.DEBUG)
    assert unlock_admin_password.run(argparse.Namespace())

    mocks["exec_in_container"].assert_called_once_with(
        settings.SERVER_CONTAINER_NAME, settings.SERVER_AXES_RESET_COMMAND
    )
    assert "Login lockouts were successfully cleared." == caplog.messages[-1]
    assert "You may now attempt to log in again." in capsys.readouterr().out


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
    assert "Failed to clear the login lockouts." == caplog.messages[-1]


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
    """Test the configured command runs axes_reset via the server's manage.py."""
    assert settings.SERVER_AXES_RESET_COMMAND == [
        "python",
        "quipucords/manage.py",
        "axes_reset",
        "--settings",
        "quipucords.settings",
    ]
