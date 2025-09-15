"""Test the "install" command."""

import logging
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
        mock.patch.object(install, "reset_secrets") as reset_secrets,
        mock.patch.object(install, "systemctl_reload") as systemctl_reload,
    ):
        reset_secrets.return_value = True

        install.run(mock_args)

        reset_secrets.assert_called_once_with(mock_args)
        systemctl_reload.assert_called_once()

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


def test_reset_secrets_happy_path(caplog):
    """Test the installer.reset_secrets helper function."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()

    with mock.patch.object(
        install, "_RESET_SECRETS_MODULE_ERROR_MESSAGE"
    ) as module_error_mapping:
        mock_reset_module_a = mock.Mock()
        mock_reset_module_a.is_set.return_value = False
        mock_reset_module_a.run.return_value = True

        mock_reset_module_b = mock.Mock()
        mock_reset_module_b.is_set.return_value = False
        mock_reset_module_b.run.return_value = True

        module_error_mapping.items.return_value = [
            (mock_reset_module_a, mock.Mock()),
            (mock_reset_module_b, mock.Mock()),
        ]

        assert install.reset_secrets(mock_args)
        assert len(caplog.messages) == 0

        mock_reset_module_a.is_set.assert_called_once()
        mock_reset_module_a.run.assert_called_once_with(mock_args)
        mock_reset_module_b.is_set.assert_called_once()
        mock_reset_module_b.run.assert_called_once_with(mock_args)


def test_reset_secrets_failure(caplog):
    """Test installer.reset_secrets when a secret reset command fails."""
    caplog.set_level(logging.ERROR)
    mock_args = mock.Mock()

    with mock.patch.object(
        install, "_RESET_SECRETS_MODULE_ERROR_MESSAGE"
    ) as module_error_mapping:
        mock_reset_module = mock.Mock()
        error_message = "uh oh!"
        module_error_mapping.items.return_value = [(mock_reset_module, error_message)]
        mock_reset_module.is_set.return_value = False
        mock_reset_module.run.return_value = False  # this is the failure

        assert not install.reset_secrets(mock_args)
        assert error_message == caplog.messages[0]
        mock_reset_module.is_set.assert_called_once()
        mock_reset_module.run.assert_called_once_with(mock_args)


def test_systemctl_reload(mock_shell_utils):
    """Test systemctl_reload invokes expected shell commands."""
    install.systemctl_reload()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(install.SYSTEMCTL_USER_RESET_FAILED_CMD, quiet=True),
            mock.call(install.SYSTEMCTL_USER_DAEMON_RELOAD_CMD, quiet=True),
        )
    )


def test_mkdirs_happy_path(temp_config_directories):
    """Test mkdirs creates directories as defined in the settings."""
    # Make at least one exist already to verify that's okay.
    assert not install.settings.SERVER_DATA_DIR.exists()
    install.settings.SERVER_DATA_DIR.mkdir(parents=True)
    install.mkdirs()
    assert install.settings.SERVER_ENV_DIR.is_dir()
    assert install.settings.SYSTEMD_UNITS_DIR.is_dir()
    assert len(install.settings.SERVER_DATA_SUBDIRS) > 0
    for subdir in install.settings.SERVER_DATA_SUBDIRS.values():
        assert subdir.is_dir()


def test_mkdirs_fails_because_expected_dir_is_a_file(temp_config_directories):
    """
    Test mkdirs fails if an expected path already exists and is not a directory.

    We do not have any special handling here. We just expect pathlib to raise OSError.
    """
    assert not install.settings.SERVER_DATA_DIR.exists()
    install.settings.SERVER_ENV_DIR.touch()
    assert not install.settings.SERVER_DATA_DIR.is_dir()
    with pytest.raises(OSError):
        install.mkdirs()
