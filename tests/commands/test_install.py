"""Test the "install" command."""

import pathlib
from collections.abc import Generator
from typing import Any
from unittest import mock

import pytest

from quipucordsctl.commands import install
from quipucordsctl.systemdunitparser import SystemdUnitParser


@pytest.fixture
def temp_config_directories(
    tmp_path: pathlib.Path, monkeypatch
) -> Generator[dict[str, pathlib.Path], Any, None]:
    """Temporarily swap any directories the "install" command would touch."""
    temp_settings_dirs = {}
    for settings_dir in ("SERVER_DATA_DIR", "SERVER_ENV_DIR", "SYSTEMD_UNITS_DIR"):
        new_path = tmp_path / settings_dir
        monkeypatch.setattr(
            f"quipucordsctl.commands.install.settings.{settings_dir}", new_path
        )
        temp_settings_dirs[settings_dir] = new_path
    tmp_data_dirs = {
        data_dir: temp_settings_dirs["SERVER_DATA_DIR"] / data_dir
        for data_dir in ("data", "db", "log", "sshkeys")
    }
    monkeypatch.setattr(
        "quipucordsctl.commands.install.settings.SERVER_DATA_SUBDIRS", tmp_data_dirs
    )
    yield temp_settings_dirs


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(install, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_install_run(
    temp_config_directories: dict[str, pathlib.Path], tmp_path: pathlib.Path, faker
):
    """
    Test the "install" command happy path.

    This test also includes two file overrides to ensure they are used correctly.
    """
    override_conf_dir = pathlib.Path(tmp_path / "override_conf_dir")
    override_conf_dir.mkdir(parents=True, exist_ok=False)

    # Define an override to exercise the path for systemd files.
    unit_override_section = "Unit"
    unit_override_key = "Description"
    unit_override_value = faker.sentence()
    with (override_conf_dir / "quipucords-app.container").open("w") as fp:
        fp.write(
            f"[{unit_override_section}]\n{unit_override_key}={unit_override_value}\n"
        )

    # Define an override to exercise the path for plain env files.
    env_override_key = "QUIPUCORDS_NETWORK_INSPECT_JOB_TIMEOUT"
    env_override_value = faker.pyint(min_value=100, max_value=1000)
    with (override_conf_dir / "env-server.env").open("w") as fp:
        fp.write(f"{env_override_key}={env_override_value}\n")

    mock_args = mock.Mock()
    mock_args.override_conf_dir = override_conf_dir
    data_dir = temp_config_directories["SERVER_DATA_DIR"]
    env_dir = temp_config_directories["SERVER_ENV_DIR"]
    systemd_dir = temp_config_directories["SYSTEMD_UNITS_DIR"]
    with (
        mock.patch.object(install, "reset_session_secret") as reset_session_secret,
        mock.patch.object(
            install, "reset_encryption_secret"
        ) as reset_encryption_secret,
        mock.patch.object(install, "reset_admin_password") as reset_admin_password,
        mock.patch.object(install, "systemctl_reload") as systemctl_reload,
    ):
        reset_session_secret.session_secret_is_set.return_value = False
        reset_encryption_secret.encryption_secret_is_set.return_value = False
        reset_admin_password.admin_password_is_set.return_value = False

        install.run(mock_args)

        # Spot-check only a few paths that should now exist.
        assert (data_dir / "data").is_dir()
        assert (env_dir / "env-app.env").is_file()
        assert (systemd_dir / "quipucords-app.container").is_file()

        # Verify the env file override was read and written.
        matching_lines = [
            line
            for line in (env_dir / "env-server.env").read_text().splitlines()
            if line.startswith(f"{env_override_key}=")
        ]
        # Check the last matching line because we simply append to env files.
        assert matching_lines[-1] == f"{env_override_key}={env_override_value}"

        # Verify the systemd unit file override was read and written.
        parser = SystemdUnitParser()
        parser.read(str((systemd_dir / "quipucords-app.container")))
        assert parser[unit_override_section][unit_override_key] == unit_override_value

        systemctl_reload.assert_called_once()
        reset_session_secret.run.assert_called_once()
        reset_encryption_secret.run.assert_called_once()
        reset_admin_password.run.assert_called_once()


def test_systemctl_reload(mock_shell_utils):
    """Test systemctl_reload invokes expected shell commands."""
    install.systemctl_reload()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(install.SYSTEMCTL_USER_RESET_FAILED_CMD, quiet=True),
            mock.call(install.SYSTEMCTL_USER_DAEMON_RELOAD_CMD, quiet=True),
        )
    )
