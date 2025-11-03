"""Test the quipucordsctl.podman_utils module."""

import logging
import pathlib
from unittest import mock

import pytest

from quipucordsctl import podman_utils, settings


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_ensure_cgroups_v2_happy_path(mock_run_command, capsys):
    """Test ensure_cgroups_v2 does nothing when cgroups v2 is enabled."""
    mock_run_command.return_value = '{"host": {"cgroupVersion": "v2"}}', None, 0

    podman_utils.ensure_cgroups_v2()
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""
    # Nothing else to assert; simply expect no output and no exceptions.


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_ensure_cgroups_v2_is_not_v2(mock_run_command, capsys):
    """Test ensure_cgroups_v2 when cgroups v2 is not enabled (RHEL8 default)."""
    mock_run_command.return_value = '{"host": {"cgroupVersion": "v1"}}', None, 0

    with pytest.raises(podman_utils.PodmanIsNotReadyError):
        podman_utils.ensure_cgroups_v2()
    assert (
        podman_utils.ENABLE_CGROUPS_V2_LONG_MESSAGE
        % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        in capsys.readouterr().out
    )
    assert capsys.readouterr().err == ""


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_ensure_cgroups_v2_fails_to_read_json(mock_run_command, capsys):
    """Test ensure_cgroups_v2 when podman info fails to return JSON."""
    mock_run_command.return_value = 'oh my potatoes\n\n""&;', None, 0

    with pytest.raises(podman_utils.PodmanIsNotReadyError):
        podman_utils.ensure_cgroups_v2()
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_ensure_cgroups_v2_failed(mock_run_command, capsys):
    """Test ensure_cgroups_v2 when podman info fails unexpectedly."""
    mock_run_command.return_value = "", None, 1

    with pytest.raises(podman_utils.PodmanIsNotReadyError):
        podman_utils.ensure_cgroups_v2()
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "os")
def test_get_socket_path_linux_default(mock_os, mock_sys, tmp_path, faker):
    """Test get_socket_path uses /run/user/uid on Linux by default."""
    mock_sys.platform = "linux"
    mock_os.environ.get.return_value = None
    uid = faker.pyint()
    mock_os.getuid.return_value = uid
    expected_socket_path = pathlib.Path(f"/run/user/{uid}/podman/podman.sock")
    assert podman_utils.get_socket_path() == expected_socket_path


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "os")
def test_get_socket_path_linux_with_xdg_env_var(mock_os, mock_sys, tmp_path):
    """Test get_socket_path uses XDG_RUNTIME_DIR on Linux if set."""
    mock_sys.platform = "linux"
    mock_os.environ.get.return_value = str(tmp_path)
    expected_socket_path = pathlib.Path(tmp_path / "podman" / "podman.sock")
    assert podman_utils.get_socket_path() == expected_socket_path
    mock_os.environ.get.assert_called_once_with("XDG_RUNTIME_DIR")


@mock.patch.object(podman_utils, "sys")
def test_get_socket_path_macos_darwin(mock_sys, tmp_path):
    """Test get_socket_path uses MACOS_DEFAULT_PODMAN_URL on macOS by default."""
    mock_sys.platform = "darwin"
    expected_socket_path = pathlib.Path(tmp_path / "podman.sock")
    with mock.patch.object(
        podman_utils, "MACOS_DEFAULT_PODMAN_URL", new=str(expected_socket_path)
    ):
        assert podman_utils.get_socket_path() == expected_socket_path


def test_get_socket_path_uses_base_url_if_given(tmp_path):
    """Test get_socket_path uses base_url if given."""
    expected_socket_path = pathlib.Path(tmp_path / "podman" / "podman.sock")
    base_url = f"unix://{expected_socket_path}"
    assert podman_utils.get_socket_path(base_url) == expected_socket_path


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
@mock.patch.object(podman_utils, "get_socket_path")
def test_ensure_podman_socket_linux(
    mock_get_socket_path, mock_shell_utils, mock_sys, tmp_path
):
    """Test ensure_podman_socket succeeds on Linux with working podman.socket."""
    mock_sys.platform = "linux"
    socket_path = pathlib.Path(tmp_path / "podman.sock")
    socket_path.touch()
    mock_get_socket_path.return_value = socket_path
    mock_shell_utils.run_command.side_effect = [("", "", 0), ("", "", 0)]

    podman_utils.ensure_podman_socket(str(socket_path))
    assert len(mock_shell_utils.run_command.call_args_list) == 2
    assert mock_shell_utils.run_command.call_args_list[0].args[0] == (
        ["systemctl", "--user", "enable", "--now", "podman.socket"]
    )
    assert mock_shell_utils.run_command.call_args_list[1].args[0] == (
        ["systemctl", "--user", "status", "podman.socket"]
    )


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
@mock.patch.object(podman_utils, "get_socket_path")
def test_ensure_podman_socket_linux_broken_podman(
    mock_get_socket_path, mock_shell_utils, mock_sys, tmp_path
):
    """Test ensure_podman_socket failure when Linux has broken podman.socket."""
    mock_sys.platform = "linux"
    mock_shell_utils.run_command.side_effect = Exception

    with pytest.raises(Exception):
        podman_utils.ensure_podman_socket()

    mock_shell_utils.run_command.assert_called_once_with(
        ["systemctl", "--user", "enable", "--now", "podman.socket"]
    )
    mock_get_socket_path.assert_not_called()


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_macos(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket succeeds when podman is enabled on macOS/darwin."""
    mock_sys.platform = "darwin"
    mock_shell_utils.run_command.side_effect = [("running", "", 0)]
    mock_path = pathlib.Path(tmp_path / "podman.sock")
    mock_path.touch()

    with mock.patch.object(
        podman_utils, "MACOS_DEFAULT_PODMAN_URL", new=str(mock_path)
    ):
        podman_utils.ensure_podman_socket()

    mock_shell_utils.run_command.assert_called_once_with(
        ["podman", "machine", "inspect", "--format", "{{.State}}"], raise_error=False
    )


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_macos_not_running(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket when podman machine is not running on macOS/darwin."""
    mock_sys.platform = "darwin"
    mock_shell_utils.run_command.side_effect = [("stopped", "", 0)]
    mock_path = pathlib.Path(tmp_path / "podman.sock")
    mock_path.touch()

    with (
        mock.patch.object(podman_utils, "MACOS_DEFAULT_PODMAN_URL", new=str(mock_path)),
        pytest.raises(podman_utils.PodmanIsNotReadyError),
    ):
        try:
            podman_utils.ensure_podman_socket()
        except podman_utils.PodmanIsNotReadyError as e:
            assert "machine is not running" in e.args[0]
            raise e

    mock_shell_utils.run_command.assert_called_once_with(
        ["podman", "machine", "inspect", "--format", "{{.State}}"], raise_error=False
    )


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_macos_broken(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket when podman command is broken on macOS/darwin."""
    mock_sys.platform = "darwin"
    mock_shell_utils.run_command.return_value = None, None, 1
    mock_path = pathlib.Path(tmp_path / "podman.sock")
    mock_path.touch()

    with (
        mock.patch.object(podman_utils, "MACOS_DEFAULT_PODMAN_URL", new=str(mock_path)),
        pytest.raises(podman_utils.PodmanIsNotReadyError),
    ):
        try:
            podman_utils.ensure_podman_socket()
        except podman_utils.PodmanIsNotReadyError as e:
            assert "failed unexpectedly" in e.args[0]
            raise e

    mock_shell_utils.run_command.assert_called_once_with(
        ["podman", "machine", "inspect", "--format", "{{.State}}"], raise_error=False
    )


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_secret_exists(mock_run_command, faker):
    """Test secret_exists simply checks the podman CLI's return code."""
    secret_name = faker.slug()
    mock_run_command.side_effect = [
        [None, None, 0],  # manual testing confirmed '0' is podman's "yes" code
        [None, None, 1],  # manual testing confirmed '1' is podman's "no" code
        [None, None, 0],
    ]

    assert podman_utils.secret_exists(secret_name)
    assert not podman_utils.secret_exists(secret_name)
    assert podman_utils.secret_exists(secret_name)


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_set_secret(mock_run_command, good_secret, faker, caplog):
    """Test the set_secret function sets a new secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    mock_run_command.side_effect = [
        [None, None, 1],  # "exists" command (no, does not exist)
        [None, None, 0],  # "create" command success
    ]

    assert podman_utils.set_secret(secret_name, good_secret)
    assert f"Podman secret '{secret_name}' was set." == caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_set_secret_exists_and_yes_replace(mock_run_command, faker, caplog):
    """Test the set_secret function replaces existing secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_run_command.side_effect = [
        [None, None, 0],  # "exists" command (yes, does exist)
        [None, None, 0],  # "delete" command success
        [None, None, 0],  # "create" command success
    ]

    assert podman_utils.set_secret(secret_name, secret_value)
    assert f"Podman secret '{secret_name}' exists." == caplog.messages[0]
    assert (
        f"Podman secret '{secret_name}' already exists before setting a new value."
        == caplog.messages[1]
    )
    assert f"Podman secret '{secret_name}' was removed." == caplog.messages[2]
    assert f"Podman secret '{secret_name}' was set." == caplog.messages[3]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_set_secret_exists_but_no_replace(mock_run_command, faker, caplog):
    """Test the set_secret function fails if secret exists but not told to replace."""
    caplog.set_level(logging.ERROR)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_run_command.side_effect = [
        [None, None, 0],  # "exists" command (yes, does exist)
        # no other commands expected
    ]

    assert not podman_utils.set_secret(secret_name, secret_value, False)
    assert (
        f"Podman secret '{secret_name}' already exists before setting a new value."
        == caplog.messages[0]
    )


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_set_secret_failed_unexpectedly(mock_run_command, faker, caplog):
    """Test the set_secret function when creating the secret fails unexpectedly."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_run_command.side_effect = [
        [None, None, 1],  # "exists" command (no, does not exist)
        [None, None, 1],  # "create" failed unexpectedly
    ]

    assert not podman_utils.set_secret(secret_name, secret_value)
    assert f"Podman failed to set secret '{secret_name}'." == caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_delete_secret(mock_run_command, faker, caplog):
    """Test the delete_secret function deletes a secret."""
    caplog.set_level(logging.INFO)
    secret_name = faker.slug()
    mock_run_command.return_value = None, None, 0  # successful delete

    assert podman_utils.delete_secret(secret_name)
    assert f"Podman secret '{secret_name}' was removed." == caplog.messages[0]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_delete_secret_non_existent(mock_run_command, faker, caplog):
    """Test the delete_secret function returns False if the secret was not there."""
    caplog.set_level(logging.INFO)
    secret_name = faker.slug()
    mock_run_command.return_value = None, None, 1  # "failed" because did not exist

    assert not podman_utils.delete_secret(secret_name)
    assert f"Podman failed to remove secret '{secret_name}'." == caplog.messages[0]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_remove_image(mock_run_command, faker, caplog):
    """Test the remove_image function removes an image."""
    caplog.set_level(logging.INFO)
    images_id = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_run_command.return_value = None, None, 0  # successful delete

    assert podman_utils.remove_image(images_id)
    assert f"Podman image '{images_id}' was removed." == caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_remove_image_already_removed(mock_run_command, faker, caplog):
    """Test the remove_image function returns true if the image is already removed."""
    caplog.set_level(logging.DEBUG)
    image_id = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_run_command.return_value = None, None, 1  # "failed" because does not exist

    assert not podman_utils.remove_image(image_id)
    assert f"Podman failed to remove image '{image_id}'." == caplog.messages[-1]


def test_list_expected_podman_container_images(
    tmp_path: pathlib.Path, monkeypatch, faker
):
    """Test test_list_expected_podman_container_images returns expected values."""
    systemd_units_dir = pathlib.Path(tmp_path) / "systemd"
    monkeypatch.setattr(
        "quipucordsctl.podman_utils.settings.SYSTEMD_UNITS_DIR",
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

    container_images = set(container_images)
    assert len(container_images) > 1
    actual_container_images = podman_utils.list_expected_podman_container_images()
    assert actual_container_images == container_images
