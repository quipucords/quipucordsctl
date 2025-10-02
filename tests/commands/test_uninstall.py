"""Test the "uninstall" command."""

import pathlib
from unittest import mock

import pytest

from quipucordsctl import settings
from quipucordsctl.commands import uninstall


@pytest.fixture
def mock_shell_utils():
    """Mock the entire shell_utils module to prevent external program execution."""
    with mock.patch.object(uninstall, "shell_utils") as mock_shell_utils:
        yield mock_shell_utils


def test_get_help():
    """Mocks the get_help method of the "uninstall" command."""
    assert (
        uninstall.get_help() == f"Uninstall the {settings.SERVER_SOFTWARE_NAME} server."
    )


def test_stop_containers(mock_shell_utils):
    """Test stop_containers invokes expected Podman commands."""
    assert uninstall.stop_containers()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_APP),
            mock.call(settings.SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK),
        )
    )


def test_remove_container_images(tmp_path: pathlib.Path, monkeypatch, faker):
    """Test remove_container_images invokes expected Podman commands."""
    systemd_units_dir = tmp_path / "systemd"
    monkeypatch.setattr(
        "quipucordsctl.commands.install.settings.SYSTEMD_UNITS_DIR",
        systemd_units_dir,
    )
    pathlib.Path.mkdir(systemd_units_dir)
    # Let's create systemd unit files with container Image paths
    container_images = []
    for unit_file in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES:
        unit_file_path = systemd_units_dir / unit_file
        if unit_file_path.suffix == ".container":
            container_image = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
            unit_file_content = (
                "\n"
                "[Unit]\n"
                "Requires=podman.socket\n"
                "\n"
                "[Container]\n"
                f"Image={container_image}\n"
            )
            unit_file_path.write_text(unit_file_content)
            container_images.append(container_image)

    with mock.patch.object(uninstall, "podman_utils") as mock_podman_utils:
        uninstall.remove_container_images()
        remove_image_calls = [
            mock.call(container_image) for container_image in container_images
        ]
        mock_podman_utils.remove_image.assert_has_calls(
            remove_image_calls, any_order=True
        )


@mock.patch("pathlib.Path.exists")
@mock.patch("pathlib.Path.unlink")
def test_remove_services(mock_unlink, mock_exists, tmp_path: pathlib.Path, monkeypatch):
    """Test remove_services invokes expected filesystem calls."""
    # Let's create a systemd generated services directory
    # so the system thinks there are services to delete there too.
    generated_services_dir = tmp_path / "generator"
    monkeypatch.setattr(
        "quipucordsctl.commands.install.settings.SYSTEMD_GENERATED_SERVICES_DIR",
        generated_services_dir,
    )

    # Make sure the system thinks all service files exist.
    mock_exists.return_value = True

    assert uninstall.remove_services()

    assert mock_unlink.call_count == len(settings.TEMPLATE_SERVER_ENV_FILENAMES) + len(
        settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES
    ) + len(settings.SYSTEMD_SERVICE_FILENAMES)


def test_reload_daemon(mock_shell_utils):
    """Test reload_daemon invokes expected shell commands."""
    assert uninstall.reload_daemon()
    mock_shell_utils.run_command.assert_has_calls(
        (
            mock.call(settings.SYSTEMCTL_USER_RESET_FAILED_CMD),
            mock.call(settings.SYSTEMCTL_USER_DAEMON_RELOAD_CMD),
        )
    )


@mock.patch("quipucordsctl.commands.uninstall.shutil.rmtree")
def test_remove_data(mock_rmtree):
    """Test remove data invokes the expected shell utilities commands."""
    uninstall.remove_data()
    expected_calls = []
    for data_dir in settings.SERVER_DATA_SUBDIRS_EXCLUDING_DB.values():
        expected_calls += [mock.call(data_dir, ignore_errors=True)]
    mock_rmtree.assert_has_calls(expected_calls)


def test_remove_secrets():
    """Test removes secrets invokes the expected Podman utilities commands."""
    with mock.patch.object(uninstall, "podman_utils") as mock_podman_utils:
        mock_podman_utils.delete_secret.return_value = True

        assert uninstall.remove_secrets()

        for key in settings.QUIPUCORDS_SECRET_KEYS:
            mock_podman_utils.delete_secret.assert_any_call(key)


def test_remove_secrets_failure():
    """Test function fails if one secret could not be removed."""
    with mock.patch.object(uninstall, "podman_utils") as mock_podman_utils:
        mock_podman_utils.delete_secret.return_value = False

        assert not uninstall.remove_secrets()

        key = list(settings.QUIPUCORDS_SECRET_KEYS)[0]
        mock_podman_utils.delete_secret.assert_any_call(key)


def test_uninstall_run(capsys):
    """Test the command invokes the expected subcommands."""
    mock_args = mock.Mock()
    with (
        mock.patch.object(uninstall, "stop_containers") as mock_stop_containers,
        mock.patch.object(
            uninstall, "remove_container_images"
        ) as mock_remove_container_images,
        mock.patch.object(uninstall, "remove_services") as mock_remove_services,
        mock.patch.object(uninstall, "reload_daemon") as mock_reload_daemon,
        mock.patch.object(uninstall, "remove_data") as mock_remove_data,
        mock.patch.object(uninstall, "remove_secrets") as mock_remove_secrets,
    ):
        mock_stop_containers.return_value = True
        mock_remove_container_images.return_value = True
        mock_remove_services.return_value = True
        mock_reload_daemon.return_value = True
        mock_remove_data.return_value = True
        mock_remove_secrets.return_value = True

        assert uninstall.run(mock_args)

        mock_stop_containers.assert_called_once()
        mock_remove_container_images.assert_called_once()
        mock_remove_services.assert_called_once()
        mock_reload_daemon.assert_called_once()
        mock_remove_data.assert_called_once()
        mock_remove_secrets.assert_called_once()

        captured = capsys.readouterr()
        uninstall_message = f"{settings.SERVER_SOFTWARE_NAME} uninstalled successfully."
        assert captured.out.strip() == uninstall_message
