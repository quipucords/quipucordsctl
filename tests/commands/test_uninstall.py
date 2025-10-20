"""Test the "uninstall" command."""

import argparse
import pathlib
from unittest import mock

from quipucordsctl import settings
from quipucordsctl.commands import uninstall


def test_get_help():
    """Mocks the get_help method of the "uninstall" command."""
    assert (
        uninstall.get_help() == f"Uninstall the {settings.SERVER_SOFTWARE_NAME} server."
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
            # let's create a bad unit file for testing Image skipping logic.
            if unit_file == "quipucords-redis.container":
                unit_file_content = f"Requires=podman.socket\nImage={container_image}\n"
            else:
                unit_file_content = (
                    "\n"
                    "[Unit]\n"
                    "Requires=podman.socket\n"
                    "\n"
                    "[Container]\n"
                    f"Image={container_image}\n"
                )
                container_images.append(container_image)
            unit_file_path.write_text(unit_file_content)

    with mock.patch.object(uninstall, "podman_utils") as mock_podman_utils:
        uninstall.remove_container_images()
        remove_image_calls = [
            mock.call(container_image) for container_image in container_images
        ]
        mock_podman_utils.remove_image.assert_has_calls(
            remove_image_calls, any_order=True
        )


def test_remove_file(tmp_path: pathlib.Path):
    """Test successful remove_file."""
    test_file = tmp_path / "test_file"

    test_file.write_text("test content")
    assert uninstall.remove_file(test_file)


def test_remove_file_does_not_exist(tmp_path: pathlib.Path):
    """Test successful remove_file if the file does not exist."""
    test_file = tmp_path / "test_file"

    assert uninstall.remove_file(test_file)


@mock.patch("pathlib.Path.unlink")
def test_remove_file_unlink_error(mock_unlink, tmp_path: pathlib.Path):
    """Test successful remove_file if the file does not exist."""
    test_file = tmp_path / "test_file"

    test_file.write_text("test content")
    mock_unlink.side_effect = Exception("unknown_exception")
    assert not uninstall.remove_file(test_file)


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
    mock_args = argparse.Namespace()
    with (
        mock.patch.object(
            uninstall.systemctl_utils, "stop_service"
        ) as mock_stop_service,
        mock.patch.object(
            uninstall, "remove_container_images"
        ) as mock_remove_container_images,
        mock.patch.object(uninstall, "remove_services") as mock_remove_services,
        mock.patch.object(
            uninstall.systemctl_utils, "reload_daemon"
        ) as mock_reload_daemon,
        mock.patch.object(uninstall, "remove_data") as mock_remove_data,
        mock.patch.object(uninstall, "remove_secrets") as mock_remove_secrets,
    ):
        mock_stop_service.return_value = True
        mock_remove_container_images.return_value = True
        mock_remove_services.return_value = True
        mock_reload_daemon.return_value = True
        mock_remove_data.return_value = True
        mock_remove_secrets.return_value = True

        mock_args.quiet = False
        assert uninstall.run(mock_args)

        mock_stop_service.assert_called_once()
        mock_remove_container_images.assert_called_once()
        mock_remove_services.assert_called_once()
        mock_reload_daemon.assert_called_once()
        mock_remove_data.assert_called_once()
        mock_remove_secrets.assert_called_once()

        captured = capsys.readouterr()
        uninstall_message = f"{settings.SERVER_SOFTWARE_NAME} uninstalled successfully."
        assert captured.out.strip() == uninstall_message


def test_uninstall_run_exits_early_if_cannot_stop(capsys):
    """Test the command exits early if "stop_services" fails."""
    mock_args = argparse.Namespace()
    with (
        mock.patch.object(
            uninstall.systemctl_utils, "stop_service"
        ) as mock_stop_service,
        mock.patch.object(
            uninstall, "remove_container_images"
        ) as mock_remove_container_images,
        mock.patch.object(uninstall, "remove_services") as mock_remove_services,
        mock.patch.object(
            uninstall.systemctl_utils, "reload_daemon"
        ) as mock_reload_daemon,
        mock.patch.object(uninstall, "remove_data") as mock_remove_data,
        mock.patch.object(uninstall, "remove_secrets") as mock_remove_secrets,
    ):
        mock_stop_service.return_value = False

        mock_args.quiet = False
        assert not uninstall.run(mock_args)

        mock_stop_service.assert_called_once()
        mock_remove_container_images.assert_not_called()
        mock_remove_services.assert_not_called()
        mock_reload_daemon.assert_not_called()
        mock_remove_data.assert_not_called()
        mock_remove_secrets.assert_not_called()

        captured = capsys.readouterr()
        assert "uninstalled successfully" not in captured.out
