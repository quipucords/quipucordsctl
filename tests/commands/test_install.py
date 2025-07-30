"""Test the "install" command."""

import pathlib
from unittest import mock

import pytest

from quipucordsctl.commands import install


@pytest.fixture
def temp_config_directories(
    tmp_path: pathlib.Path, monkeypatch
) -> dict[str, pathlib.Path]:
    """Temporarily swap any directories the install command would touch."""
    temp_settings_dirs = {}
    for settings_dir in ("SERVER_DATA_DIR", "SERVER_ENV_DIR", "SYSTEMD_UNITS_DIR"):
        new_path = tmp_path / settings_dir
        monkeypatch.setattr(
            f"quipucordsctl.commands.install.settings.{settings_dir}", new_path
        )
        temp_settings_dirs[settings_dir] = new_path
    yield temp_settings_dirs


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(install, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_install_run(temp_config_directories: dict[str, pathlib.Path]):
    """Test the install command happy path."""
    mock_args = mock.Mock()
    mock_args.override_conf_dir = None
    data_dir = temp_config_directories["SERVER_DATA_DIR"]
    env_dir = temp_config_directories["SERVER_ENV_DIR"]
    systemd_dir = temp_config_directories["SYSTEMD_UNITS_DIR"]
    with (
        mock.patch.object(
            install, "reset_application_secret"
        ) as reset_application_secret,
        mock.patch.object(install, "reset_admin_password") as reset_admin_password,
        mock.patch.object(install, "systemctl_reload") as systemctl_reload,
    ):
        reset_application_secret.application_secret_is_set.return_value = False
        reset_admin_password.admin_password_is_set.return_value = False

        install.run(mock_args)

        # Spot-check only a few paths that should now exist.
        assert (data_dir / "data").is_dir()
        assert (env_dir / "env-app.env").is_file()
        assert (systemd_dir / "quipucords-app.container").is_file()

        systemctl_reload.assert_called_once()
        reset_application_secret.run.assert_called_once()
        reset_admin_password.run.assert_called_once()


def test_systemctl_reload(mock_shell_utils):
    """Test systemctl_reload invokes expected shell commands."""
    install.systemctl_reload()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(install.SYSTEMCTL_USER_RESET_FAILED_CMD),
            mock.call(install.SYSTEMCTL_USER_DAEMON_RELOAD_CMD),
        )
    )
