"""Test the quipucordsctl.podman_utils module."""

import logging
import pathlib
import subprocess
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
    assert f"Removed container image '{images_id}'." == caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_remove_image_already_removed(mock_run_command, faker, caplog):
    """Test the remove_image function returns true if the image is already removed."""
    caplog.set_level(logging.DEBUG)
    image_id = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_run_command.return_value = None, None, 1  # "failed" because does not exist

    assert not podman_utils.remove_image(image_id)
    assert f"Failed to remove container image '{image_id}'." == caplog.messages[-1]


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


@pytest.mark.parametrize(
    "image_name,expected_registry",
    (
        ("example.com/foo/bar", "example.com"),
        ("example.com/foo/bar:biz", "example.com"),
        ("example.com/bar", "example.com"),
        ("example.com/bar:biz", "example.com"),
        ("example.com:8888/foo/bar", "example.com:8888"),
        ("example.com:8888/foo/bar:biz", "example.com:8888"),
        ("localhost/bar:biz", "localhost"),
        ("bar:biz", settings.DEFAULT_PODMAN_REGISTRY),
        ("bar", settings.DEFAULT_PODMAN_REGISTRY),
    ),
)
def test_get_registry_from_image_name(image_name, expected_registry):
    """Test get_registry_from_image_name returns expected values."""
    registry = podman_utils.get_registry_from_image_name(image_name)
    assert registry == expected_registry


@mock.patch.object(podman_utils, "shell_utils")
def test_pull_image(mock_shell_utils, faker):
    """Test pull_image returns True on the happy path."""
    mock_shell_utils.run_command.return_value = None, None, 0
    image_name = faker.slug()
    assert podman_utils.pull_image(image_name)


@mock.patch.object(podman_utils, "shell_utils")
def test_pull_image_error(mock_shell_utils, faker, caplog):
    """Test pull_image logs an error and returns False returns when an error occurs."""
    caplog.set_level(logging.ERROR)
    mock_shell_utils.run_command.return_value = None, None, 1
    image_name = faker.slug()
    assert not podman_utils.pull_image(image_name)
    assert image_name in caplog.messages[-1]


def test_verify_podman_argument_string(faker):
    """Test verify_podman_argument_string passes silently with valid inputs."""
    podman_utils.verify_podman_argument_string(faker.word(), faker.word())
    podman_utils.verify_podman_argument_string(faker.word(), faker.slug())
    podman_utils.verify_podman_argument_string(faker.word(), faker.sentence())
    assert True  # just to assert that no exceptions were raised


@pytest.mark.parametrize("value", (["a"], {"a": "b"}, None, True, 1.0, 1e1, object))
def test_verify_podman_argument_string_type_error(value):
    """Test verify_podman_argument_string raises TypeError."""
    with pytest.raises(TypeError):
        podman_utils.verify_podman_argument_string("thing", value)


@pytest.mark.parametrize("value", (" ", "\t", "\n", "    "))
def test_verify_podman_argument_string_value_error(value):
    """Test verify_podman_argument_string raises ValueError."""
    with pytest.raises(ValueError):
        podman_utils.verify_podman_argument_string("thing", value)


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_get_secret_value_success(mock_run_command, faker):
    """Test get_secret_value returns the secret value when it exists."""
    secret_name = faker.slug()
    secret_value = faker.password()
    mock_run_command.side_effect = [
        [None, None, 0],
        [secret_value, None, 0],
    ]

    result = podman_utils.get_secret_value(secret_name)
    assert result == secret_value


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_get_secret_value_not_exists(mock_run_command, faker):
    """Test get_secret_value returns None when secret does not exist."""
    secret_name = faker.slug()
    mock_run_command.side_effect = [
        [None, None, 1],
    ]

    result = podman_utils.get_secret_value(secret_name)
    assert result is None


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_get_secret_value_inspect_fails(mock_run_command, faker, caplog):
    """Test get_secret_value returns None when inspect command fails unexpectedly."""
    caplog.set_level(logging.DEBUG)
    secret_name = faker.slug()
    mock_run_command.side_effect = [
        [None, None, 0],
        [None, None, 1],  # "inspect" command failed
    ]

    result = podman_utils.get_secret_value(secret_name)
    assert result is None
    assert f"Failed to retrieve podman secret '{secret_name}'." in caplog.messages[-1]


@pytest.mark.parametrize("value", (None, 123, ["list"], {"dict": "value"}))
def test_get_secret_value_invalid_type(value):
    """Test get_secret_value raises TypeError for non-string inputs."""
    with pytest.raises(TypeError):
        podman_utils.get_secret_value(value)


@pytest.mark.parametrize("value", ("", " ", "\t", "\n", "   "))
def test_get_secret_value_empty_string(value):
    """Test get_secret_value raises ValueError for empty/whitespace strings."""
    with pytest.raises(ValueError):
        podman_utils.get_secret_value(value)


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_get_secret_value_calls_correct_command(mock_run_command, faker):
    """Test get_secret_value calls podman with correct arguments."""
    secret_name = faker.slug()
    mock_run_command.side_effect = [
        [None, None, 0],
        ["secret_data", None, 0],
    ]

    podman_utils.get_secret_value(secret_name)

    inspect_call = mock_run_command.call_args_list[1]
    assert inspect_call.args[0] == [
        "podman",
        "secret",
        "inspect",
        "--showsecret",
        "--format",
        "{{.SecretData}}",
        secret_name,
    ]
    assert inspect_call.kwargs.get("raise_error") is False
    assert inspect_call.kwargs.get("redact_output") is True


@pytest.mark.parametrize(
    "secret_value",
    [
        " password_with_leading_space",
        "password_with_trailing_space ",
        " password_with_both_spaces ",
        "  password  ",
        "\tpassword_with_tab",
    ],
)
@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_get_secret_value_preserves_whitespace(mock_run_command, secret_value):
    """Test get_secret_value preserves leading/trailing whitespace in secret values."""
    secret_name = "test-secret"
    mock_run_command.side_effect = [
        [None, None, 0],
        [secret_value, None, 0],
    ]

    result = podman_utils.get_secret_value(secret_name)
    assert result == secret_value


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_image_exists_returns_true_when_image_exists(mock_run_command, faker, caplog):
    """Test image_exists returns True when image exists locally."""
    caplog.set_level(logging.DEBUG)
    image_name = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_run_command.return_value = None, None, 0

    assert podman_utils.image_exists(image_name)
    mock_run_command.assert_called_once_with(
        ["podman", "image", "exists", image_name], raise_error=False
    )
    assert f"Container image '{image_name}' exists locally." in caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_image_exists_returns_false_when_image_not_found(
    mock_run_command, faker, caplog
):
    """Test image_exists returns False when image does not exist locally."""
    caplog.set_level(logging.DEBUG)
    image_name = f"quay.io/{faker.slug()}/{faker.slug()}:latest"
    mock_run_command.return_value = None, None, 1

    assert not podman_utils.image_exists(image_name)
    mock_run_command.assert_called_once_with(
        ["podman", "image", "exists", image_name], raise_error=False
    )
    assert (
        f"Container image '{image_name}' does not exist locally." in caplog.messages[-1]
    )


@pytest.mark.parametrize("value", (None, 123, ["list"], {"dict": "value"}))
def test_image_exists_raises_type_error_for_non_string(value):
    """Test image_exists raises TypeError for non-string inputs."""
    with pytest.raises(TypeError):
        podman_utils.image_exists(value)


@pytest.mark.parametrize("value", ("", " ", "\t", "\n", "   "))
def test_image_exists_raises_value_error_for_empty_string(value):
    """Test image_exists raises ValueError for empty/whitespace strings."""
    with pytest.raises(ValueError):
        podman_utils.image_exists(value)


@mock.patch.object(podman_utils, "image_exists")
@mock.patch.object(podman_utils, "list_expected_podman_container_images")
def test_get_missing_images_all_present(
    mock_list_expected, mock_image_exists, faker, caplog
):
    """Test get_missing_images returns empty set when all images exist."""
    caplog.set_level(logging.DEBUG)
    expected_images = {
        f"quay.io/{faker.slug()}/{faker.slug()}:latest",
        f"quay.io/{faker.slug()}/{faker.slug()}:latest",
    }
    mock_list_expected.return_value = expected_images
    mock_image_exists.return_value = True

    result = podman_utils.get_missing_images()

    assert result == set()
    assert mock_image_exists.call_count == len(expected_images)
    assert "All required images are present locally." in caplog.messages[-1]


@mock.patch.object(podman_utils, "image_exists")
@mock.patch.object(podman_utils, "list_expected_podman_container_images")
def test_get_missing_images_some_missing(
    mock_list_expected, mock_image_exists, faker, caplog
):
    """Test get_missing_images returns only the missing images."""
    caplog.set_level(logging.DEBUG)
    present_image = f"quay.io/{faker.slug()}/present:latest"
    missing_image = f"quay.io/{faker.slug()}/missing:latest"
    expected_images = {present_image, missing_image}
    mock_list_expected.return_value = expected_images
    mock_image_exists.side_effect = lambda img: {
        present_image: True,
        missing_image: False,
    }[img]

    result = podman_utils.get_missing_images()

    assert result == {missing_image}
    assert "Missing 1 of 2 required images." in caplog.messages[-1]


@mock.patch.object(podman_utils, "image_exists")
@mock.patch.object(podman_utils, "list_expected_podman_container_images")
def test_get_missing_images_all_missing(
    mock_list_expected, mock_image_exists, faker, caplog
):
    """Test get_missing_images returns all images when none exist locally."""
    caplog.set_level(logging.DEBUG)
    expected_images = {
        f"quay.io/{faker.slug()}/{faker.slug()}:latest",
        f"quay.io/{faker.slug()}/{faker.slug()}:latest",
        f"quay.io/{faker.slug()}/{faker.slug()}:latest",
    }
    mock_list_expected.return_value = expected_images
    mock_image_exists.return_value = False

    result = podman_utils.get_missing_images()

    assert result == expected_images
    assert (
        f"Missing {len(expected_images)} of {len(expected_images)}"
        in caplog.messages[-1]
    )


@mock.patch.object(podman_utils, "image_exists")
@mock.patch.object(podman_utils, "list_expected_podman_container_images")
def test_get_missing_images_empty_expected(
    mock_list_expected, mock_image_exists, caplog
):
    """Test get_missing_images handles case with no expected images."""
    caplog.set_level(logging.DEBUG)
    mock_list_expected.return_value = set()

    result = podman_utils.get_missing_images()

    assert result == set()
    mock_image_exists.assert_not_called()
    assert "All required images are present locally." in caplog.messages[-1]


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_check_registry_login_logged_in(mock_run_command, caplog):
    """Test check_registry_login returns True when credentials are valid."""
    caplog.set_level(logging.DEBUG)
    registry = "registry.redhat.io"
    mock_run_command.return_value = "", None, 0

    assert podman_utils.check_registry_login(registry)
    mock_run_command.assert_called_once_with(
        ["podman", "login", registry],
        raise_error=False,
        stdin="",
        stderr=subprocess.DEVNULL,
    )
    assert (
        f"Valid credentials already exist for registry '{registry}'."
        in caplog.messages[-1]
    )


@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_check_registry_login_not_logged_in(mock_run_command, caplog):
    """Test check_registry_login returns False when user is not logged in."""
    caplog.set_level(logging.DEBUG)
    registry = "registry.redhat.io"
    mock_run_command.return_value = "", None, 125

    assert not podman_utils.check_registry_login(registry)
    mock_run_command.assert_called_once_with(
        ["podman", "login", registry],
        raise_error=False,
        stdin="",
        stderr=subprocess.DEVNULL,
    )
    assert f"Not logged in to registry '{registry}'." in caplog.messages[-1]


@mock.patch.object(podman_utils, "getpass")
@mock.patch("builtins.input")
@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_login_to_registry_success(  # noqa: PLR0913
    mock_run_command, mock_input, mock_getpass, faker, caplog, capsys
):
    """Test login_to_registry returns True on successful login."""
    caplog.set_level(logging.INFO)
    registry = "registry.redhat.io"
    username = faker.user_name()
    password = faker.password()

    mock_input.return_value = username
    mock_getpass.getpass.return_value = password
    mock_run_command.return_value = None, None, 0

    assert podman_utils.login_to_registry(registry)

    mock_run_command.assert_called_once_with(
        ["podman", "login", registry, "--username", username, "--password-stdin"],
        raise_error=False,
        stdin=password,
        redact_output=False,
    )
    assert f"Successfully logged in to registry '{registry}'." in caplog.messages[-1]
    assert "Logging in to" in capsys.readouterr().out


@mock.patch.object(podman_utils, "getpass")
@mock.patch("builtins.input")
@mock.patch.object(podman_utils.shell_utils, "run_command")
def test_login_to_registry_failure(
    mock_run_command, mock_input, mock_getpass, faker, caplog
):
    """Test login_to_registry returns False when podman login fails."""
    caplog.set_level(logging.ERROR)
    registry = "registry.redhat.io"

    mock_input.return_value = faker.user_name()
    mock_getpass.getpass.return_value = faker.password()
    mock_run_command.return_value = None, "Login failed", 1

    assert not podman_utils.login_to_registry(registry)
    assert f"Failed to log in to registry '{registry}'." in caplog.messages[-1]


@mock.patch.object(podman_utils, "getpass")
@mock.patch("builtins.input")
def test_login_to_registry_empty_username(mock_input, mock_getpass, caplog):
    """Test login_to_registry returns False when username is empty."""
    caplog.set_level(logging.ERROR)
    registry = "registry.redhat.io"

    mock_input.return_value = "   "
    mock_getpass.getpass.return_value = "password"

    assert not podman_utils.login_to_registry(registry)
    assert "Username cannot be empty." in caplog.messages[-1]


@mock.patch.object(podman_utils, "getpass")
@mock.patch("builtins.input")
def test_login_to_registry_empty_password(mock_input, mock_getpass, faker, caplog):
    """Test login_to_registry returns False when password is empty."""
    caplog.set_level(logging.ERROR)
    registry = "registry.redhat.io"

    mock_input.return_value = faker.user_name()
    mock_getpass.getpass.return_value = ""

    assert not podman_utils.login_to_registry(registry)
    assert "Password cannot be empty." in caplog.messages[-1]


@mock.patch.object(podman_utils.settings, "runtime")
def test_login_to_registry_quiet_mode(mock_runtime):
    """Test login_to_registry returns False in quiet mode without prompting."""
    mock_runtime.quiet = True
    registry = "registry.redhat.io"

    assert not podman_utils.login_to_registry(registry)


@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_all_present(mock_get_missing, caplog):
    """Test ensure_images returns True when all images are present."""
    caplog.set_level(logging.INFO)
    mock_get_missing.return_value = set()

    assert podman_utils.ensure_images()
    assert "All required container images are present." in caplog.messages[-1]


@mock.patch.object(podman_utils, "pull_image")
@mock.patch.object(podman_utils, "check_registry_login")
@mock.patch.object(podman_utils, "get_registry_from_image_name")
@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_pull_success(  # noqa: PLR0913
    mock_get_missing,
    mock_confirm,
    mock_get_registry,
    mock_check_login,
    mock_pull,
    faker,
    caplog,
):
    """Test ensure_images returns True when images are pulled successfully."""
    caplog.set_level(logging.INFO)
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = True
    mock_get_registry.return_value = "registry.redhat.io"
    mock_check_login.return_value = True
    mock_pull.return_value = True

    assert podman_utils.ensure_images()

    mock_pull.assert_called_once_with(missing_image)
    assert "Required container image" in caplog.text and "is missing" in caplog.text
    assert "All required images have been pulled successfully." in caplog.text


@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_user_declines(mock_get_missing, mock_confirm, faker, caplog):
    """Test ensure_images returns False when user declines to download."""
    caplog.set_level(logging.INFO)
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = False

    assert not podman_utils.ensure_images()

    assert "disconnected installation" in caplog.text.lower()


@mock.patch.object(podman_utils, "login_to_registry")
@mock.patch.object(podman_utils, "check_registry_login")
@mock.patch.object(podman_utils, "get_registry_from_image_name")
@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_login_required_and_succeeds(  # noqa: PLR0913
    mock_get_missing,
    mock_confirm,
    mock_get_registry,
    mock_check_login,
    mock_login,
    faker,
):
    """Test ensure_images handles login when not already logged in."""
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = True
    mock_get_registry.return_value = "registry.redhat.io"
    mock_check_login.return_value = False
    mock_login.return_value = True

    with mock.patch.object(podman_utils, "pull_image", return_value=True):
        assert podman_utils.ensure_images()

    mock_login.assert_called_once_with("registry.redhat.io")


@mock.patch.object(podman_utils, "login_to_registry")
@mock.patch.object(podman_utils, "check_registry_login")
@mock.patch.object(podman_utils, "get_registry_from_image_name")
@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_login_fails(  # noqa: PLR0913
    mock_get_missing,
    mock_confirm,
    mock_get_registry,
    mock_check_login,
    mock_login,
    faker,
):
    """Test ensure_images returns False when login fails."""
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = True
    mock_get_registry.return_value = "registry.redhat.io"
    mock_check_login.return_value = False
    mock_login.return_value = False

    assert not podman_utils.ensure_images()


@mock.patch.object(podman_utils, "pull_image")
@mock.patch.object(podman_utils, "check_registry_login")
@mock.patch.object(podman_utils, "get_registry_from_image_name")
@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_pull_fails(  # noqa: PLR0913
    mock_get_missing,
    mock_confirm,
    mock_get_registry,
    mock_check_login,
    mock_pull,
    faker,
):
    """Test ensure_images returns False when pull fails."""
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = True
    mock_get_registry.return_value = "registry.redhat.io"
    mock_check_login.return_value = True
    mock_pull.return_value = False

    assert not podman_utils.ensure_images()


@mock.patch.object(podman_utils.settings, "runtime")
@mock.patch.object(podman_utils.shell_utils, "confirm")
@mock.patch.object(podman_utils, "get_missing_images")
def test_ensure_images_quiet_mode_no_output(
    mock_get_missing, mock_confirm, mock_runtime, faker, capsys
):
    """Test ensure_images produces no output in quiet mode when user declines."""
    mock_runtime.quiet = True
    missing_image = f"registry.redhat.io/{faker.slug()}:latest"
    mock_get_missing.return_value = {missing_image}
    mock_confirm.return_value = False

    assert not podman_utils.ensure_images()

    output = capsys.readouterr().out
    assert output == ""
