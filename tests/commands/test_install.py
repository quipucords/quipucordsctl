"""Test the "install" command."""

import pathlib
import tempfile
from unittest import mock

import pytest

from quipucordsctl.commands import install


@pytest.fixture
def temp_config_directories() -> tuple[str]:
    """Temporarily swap any directories the install command would touch."""
    with (
        tempfile.TemporaryDirectory() as data_dir,
        tempfile.TemporaryDirectory() as env_dir,
        tempfile.TemporaryDirectory() as systemd_dir,
    ):
        with mock.patch(
            "quipucordsctl.commands.install.settings.SERVER_DATA_DIR",
            new=pathlib.Path(data_dir),
        ), mock.patch(
            "quipucordsctl.commands.install.settings.SERVER_ENV_DIR",
            new=pathlib.Path(env_dir),
        ), mock.patch(
            "quipucordsctl.commands.install.settings.SYSTEMD_UNITS_DIR",
            new=pathlib.Path(systemd_dir),
        ):
            yield data_dir, env_dir, systemd_dir


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(install, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_install_run(temp_config_directories):
    """Test the install command happy path."""
    data_dir, env_dir, systemd_dir = temp_config_directories
    with (
        mock.patch.object(install, "reset_django_secret") as reset_django_secret,
        mock.patch.object(install, "reset_server_password") as reset_server_password,
        mock.patch.object(install, "systemctl_reload") as systemctl_reload,
    ):
        reset_django_secret.django_secret_is_set.return_value = False
        reset_server_password.server_password_is_set.return_value = False

        install.run()

        # Spot-check only a few paths that should now exist.
        assert (pathlib.Path(data_dir) / "data").is_dir()
        assert (pathlib.Path(env_dir) / "env-app.env").is_file()
        assert (pathlib.Path(systemd_dir) / "quipucords-app.container").is_file()

        systemctl_reload.assert_called_once()
        reset_django_secret.run.assert_called_once()
        reset_server_password.run.assert_called_once()


def test_systemctl_reload(mock_shell_utils):
    """Test systemctl_reload invokes expected shell commands."""
    install.systemctl_reload()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(install.SYSTEMCTL_USER_RESET_FAILED_CMD),
            mock.call(install.SYSTEMCTL_USER_DAEMON_RELOAD_CMD),
        )
    )
