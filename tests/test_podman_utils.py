"""Test the quipucordsctl.podman_utils module."""

import logging
import pathlib
from unittest import mock

import pytest
from podman import errors as podman_errors

from quipucordsctl import podman_utils, settings


@mock.patch.object(podman_utils, "get_podman_client")
def test_ensure_cgroups_v2_happy_path(mock_get_podman_client, capsys):
    """Test ensure_cgroups_v2 does nothing when cgroups v2 is enabled."""
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.info.return_value = {"host": {"cgroupVersion": "v2"}}

    podman_utils.ensure_cgroups_v2()
    assert capsys.readouterr().out == ""
    assert capsys.readouterr().err == ""
    # Nothing else to assert; simply expect no output and no exceptions.


@mock.patch.object(podman_utils, "get_podman_client")
def test_ensure_cgroups_v2_failed(mock_get_podman_client, capsys):
    """Test ensure_cgroups_v2 when cgroups v2 is not enabled (RHEL8 default)."""
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.info.return_value = {"host": {"cgroupVersion": "v1"}}

    with pytest.raises(podman_utils.PodmanIsNotReadyError):
        podman_utils.ensure_cgroups_v2()
    assert (
        podman_utils.ENABLE_CGROUPS_V2_LONG_MESSAGE
        % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
        in capsys.readouterr().out
    )
    assert capsys.readouterr().err == ""


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
@mock.patch.object(podman_utils, "xdg")
def test_ensure_podman_socket(mock_xdg, mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket does nothing when podman socket is default path."""
    mock_sys.platform = "linux"
    socket_path = pathlib.Path(tmp_path / "podman" / "podman.sock")
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    socket_path.touch()
    mock_shell_utils.run_command.side_effect = [("", "", 0), ("", "", 0)]
    mock_xdg.BaseDirectory.get_runtime_dir.return_value = str(tmp_path)

    podman_utils.ensure_podman_socket()
    assert len(mock_shell_utils.run_command.call_args_list) == 2


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_custom_path(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket does nothing when podman socket has custom path."""
    mock_sys.platform = "linux"
    socket_path = pathlib.Path(tmp_path / "podman.sock")
    socket_path.touch()
    mock_shell_utils.run_command.side_effect = [("", "", 0), ("", "", 0)]

    podman_utils.ensure_podman_socket(str(socket_path))
    assert len(mock_shell_utils.run_command.call_args_list) == 2


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_macos(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket does nothing when podman is enabled on macOS/darwin."""
    mock_sys.platform = "darwin"
    mock_shell_utils.run_command.side_effect = [("running", "", 0)]
    mock_path = pathlib.Path(tmp_path / "podman.sock")
    mock_path.touch()

    with mock.patch.object(
        podman_utils, "MACOS_DEFAULT_PODMAN_URL", new=str(mock_path)
    ):
        podman_utils.ensure_podman_socket()

    mock_shell_utils.run_command.assert_called_once_with(
        podman_utils.PODMAN_MACHINE_STATE_CMD
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
        podman_utils.PODMAN_MACHINE_STATE_CMD
    )


@mock.patch.object(podman_utils, "sys")
@mock.patch.object(podman_utils, "shell_utils")
def test_ensure_podman_socket_macos_broken(mock_shell_utils, mock_sys, tmp_path):
    """Test ensure_podman_socket when podman command is broken on macOS/darwin."""
    mock_sys.platform = "darwin"
    mock_shell_utils.run_command.side_effect = [Exception]
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
        podman_utils.PODMAN_MACHINE_STATE_CMD
    )


@mock.patch.object(podman_utils, "get_podman_client")
def test_secret_exists(mock_get_podman_client, faker):
    """Test the secret_exists function is a simple facade over the podman client."""
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.side_effect = [True, False, True]

    assert podman_utils.secret_exists(secret_name)
    assert not podman_utils.secret_exists(secret_name)
    assert podman_utils.secret_exists(secret_name)


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret(mock_get_podman_client, good_secret, faker, caplog):
    """Test the set_secret function sets a new secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = False

    assert podman_utils.set_secret(secret_name, good_secret)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_called_once_with(secret_name, good_secret)
    assert f"New podman secret {secret_name} was set." == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_exists_ans_yes_replace(mock_get_podman_client, faker, caplog):
    """Test the set_secret function replaces existing secret."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert podman_utils.set_secret(secret_name, secret_value)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_called_once_with(secret_name)
    mock_podman_client.secrets.create.assert_called_once_with(secret_name, secret_value)
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]
    assert f"Old podman secret {secret_name} was removed." == caplog.messages[1]
    assert f"New podman secret {secret_name} was set." == caplog.messages[2]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_exists_but_no_replace(mock_get_podman_client, faker, caplog):
    """Test the set_secret function fails if secret exists but not told to replace."""
    caplog.set_level(logging.ERROR)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert not podman_utils.set_secret(secret_name, secret_value, False)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_not_called()
    mock_podman_client.secrets.create.assert_not_called()
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_set_secret_unhandled_exception(mock_get_podman_client, faker, caplog):
    """
    Test the set_secret function lets exceptions raise up to caller.

    This is okay because we expect main.main to handle all exceptions and exit cleanly.
    """
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True
    mock_podman_client.secrets.remove.side_effect = podman_errors.PodmanError

    with pytest.raises(podman_errors.PodmanError):
        podman_utils.set_secret(secret_name, secret_value)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_called_once_with(secret_name)
    mock_podman_client.secrets.create.assert_not_called()
    assert f"A podman secret {secret_name} already exists." == caplog.messages[0]
    assert len(caplog.messages) == 1


@mock.patch.object(podman_utils, "get_podman_client")
def test_delete_secret(mock_get_podman_client, faker, caplog):
    """Test the delete_secret function deletes a secret."""
    caplog.set_level(logging.INFO)
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = True

    assert podman_utils.delete_secret(secret_name)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_called_once_with(secret_name)
    assert f"Podman secret {secret_name} was removed." == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_delete_secret_non_existent(mock_get_podman_client, faker):
    """Test the delete_secret function does nothing if the secret is not there."""
    secret_name = faker.slug()
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.secrets.exists.return_value = False

    assert podman_utils.delete_secret(secret_name)

    mock_podman_client.secrets.exists.assert_called_once_with(secret_name)
    mock_podman_client.secrets.remove.assert_not_called()


@mock.patch.object(podman_utils, "get_podman_client")
def test_remove_image(mock_get_podman_client, faker, caplog):
    """Test the remove_image function removes an image."""
    caplog.set_level(logging.INFO)
    image_ref = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.images.remove.return_value = True

    assert podman_utils.remove_image(image_ref)

    mock_podman_client.images.remove.assert_called_once_with(image_ref)
    assert f"Removing the container image {image_ref}" == caplog.messages[0]


@mock.patch.object(podman_utils, "get_podman_client")
def test_remove_image_already_removed(mock_get_podman_client, faker, caplog):
    """Test the remove_image function returns true if the image is already removed."""
    caplog.set_level(logging.INFO)
    image_ref = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.images.remove.side_effect = podman_errors.ImageNotFound(
        image_ref
    )

    assert podman_utils.remove_image(image_ref)

    mock_podman_client.images.remove.assert_called_once_with(image_ref)
    assert f"Removing the container image {image_ref}" == caplog.messages[0]
    assert (
        f"Podman could not remove image {image_ref} - Image not found."
        == caplog.messages[1]
    )


@mock.patch.object(podman_utils, "get_podman_client")
def test_remove_image_podman_api_error(mock_get_podman_client, faker, caplog):
    """Test the remove_image function returns false if the Podman API call fails."""
    caplog.set_level(logging.INFO)
    image_ref = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_podman_client = mock_get_podman_client.return_value.__enter__.return_value
    mock_podman_client.images.remove.side_effect = podman_errors.APIError(image_ref)

    assert not podman_utils.remove_image(image_ref)

    mock_podman_client.images.remove.assert_called_once_with(image_ref)
    assert f"Removing the container image {image_ref}" == caplog.messages[0]
    assert (
        f"Podman could not remove image {image_ref} - Failed Podman API call."
        == caplog.messages[1]
    )
