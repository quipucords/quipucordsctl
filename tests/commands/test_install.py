"""Test the "install" command."""

import argparse
import logging
import pathlib
from unittest import mock

import pytest

from quipucordsctl import settings, shell_utils
from quipucordsctl.commands import install
from quipucordsctl.systemdunitparser import SystemdUnitParser


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(install, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_get_help():
    """Test the get_help returns an appropriate string."""
    assert settings.SERVER_SOFTWARE_NAME in install.get_help()


def test_get_description():
    """Test the get_description returns an appropriate string."""
    assert "`install`" in install.get_description()


@pytest.mark.parametrize(
    "args,attr_name,expected",
    (
        (["--no-linger"], "no_linger", True),
        (["-L"], "no_linger", True),
        ([], "no_linger", False),
    ),
)
def test_setup_parser(args, attr_name, expected):
    """Test the setup_parser configures parser as expected."""
    parser = argparse.ArgumentParser()
    install.setup_parser(parser)

    value = getattr(parser.parse_args(args), attr_name)
    if type(expected) is bool:
        assert value is expected
    else:
        assert value == expected


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
        mock.patch.object(install, "podman_utils") as podman_utils,
        mock.patch.object(install, "systemctl_utils") as systemctl_utils,
        mock.patch.object(install, "reset_secrets") as reset_secrets,
        mock.patch.object(install, "systemctl_reload") as systemctl_reload,
        mock.patch.object(install, "loginctl_utils") as loginctl_utils,
    ):
        reset_secrets.return_value = True
        loginctl_utils.enable_linger.return_value = True

        install.run(mock_args)

        podman_utils.ensure_podman_socket.assert_called_once()
        podman_utils.ensure_cgroups_v2.assert_called_once()
        systemctl_utils.ensure_systemd_user_session.assert_called_once()
        reset_secrets.assert_called_once_with(mock_args)
        systemctl_reload.assert_called_once()
        loginctl_utils.enable_linger.assert_called_once()

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
            mock.call(settings.SYSTEMCTL_USER_RESET_FAILED_CMD),
            mock.call(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD),
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


def test_update_systemd_template_config_with_overrides_missing_header(
    tmp_path: pathlib.Path, caplog
):
    """Test handling malformed systemd-style override file with no section headers."""
    caplog.set_level(logging.WARNING)

    template_filename = "quipucords-app.container"
    override_conf_path = pathlib.Path(tmp_path / template_filename)
    override_conf_path.write_text("Oops! This file has no section headers.")

    template_config = SystemdUnitParser()

    template_path = shell_utils.systemd_template_dir() / template_filename
    template_config = SystemdUnitParser()
    template_config.read(template_path)

    install._update_systemd_template_config_with_overrides(
        template_filename, template_config, override_conf_path
    )

    assert caplog.messages[0].startswith(f"Skipping overrides for {template_filename}")
