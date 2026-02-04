"""Functions to simplify interfacing with podman."""

import configparser
import getpass
import json
import logging
import os
import pathlib
import subprocess
import sys
import textwrap
from gettext import gettext as _
from urllib import parse

from quipucordsctl import settings, shell_utils, systemdunitparser

logger = logging.getLogger(__name__)
MACOS_DEFAULT_PODMAN_URL = "unix:///var/run/docker.sock"
ENABLE_CGROUPS_V2_LONG_MESSAGE = _(
    textwrap.dedent(
        """
        This system is not configured to use cgroups v2 which is required for %(server_software_name)s.
        To enable cgroups v2 (a.k.a. cgroup2fs), you may need to update your kernel arguments and reboot.
        Please run the following commands before using %(server_software_name)s:

            sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"
            sudo reboot
        """  # noqa: E501
    ).strip()
)


class PodmanIsNotReadyError(Exception):
    """Exception raised when podman is not ready."""


def get_socket_path(base_url: str | None = None) -> pathlib.Path:
    """Get the podman socket path."""
    if base_url:
        url_or_path = base_url
    elif sys.platform == "darwin":
        url_or_path = MACOS_DEFAULT_PODMAN_URL
    else:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
        url_or_path = str(pathlib.Path(runtime_dir) / "podman" / "podman.sock")
    return pathlib.Path(parse.urlparse(url_or_path).path)


def ensure_podman_socket(base_url: str | None = None):
    """Ensure podman socket is available, as required by the Podman client."""
    logger.debug(_("Ensuring Podman socket is available."))

    if sys.platform == "darwin":
        stdout, __, exit_code = shell_utils.run_command(
            ["podman", "machine", "inspect", "--format", "{{.State}}"],
            raise_error=False,
        )
        if exit_code != 0:
            raise PodmanIsNotReadyError(
                _(
                    "Podman command failed unexpectedly. Please install Podman and "
                    "run `podman machine start` before using this command."
                )
            )
        if stdout.strip() != "running":
            raise PodmanIsNotReadyError(
                _(
                    "Podman machine is not running. Please install Podman and "
                    "run `podman machine start` before using this command."
                )
            )
    else:
        try:
            shell_utils.run_command(
                ["systemctl", "--user", "enable", "--now", "podman.socket"]
            )
            shell_utils.run_command(["systemctl", "--user", "status", "podman.socket"])
        except Exception as e:
            logger.error(
                _(
                    "The 'podman.socket' service failed to start. "
                    "Please check logs and ensure that Podman is correctly installed."
                )
            )
            raise e

    socket_path = get_socket_path(base_url)
    if not socket_path.exists():
        raise PodmanIsNotReadyError(
            _(
                "Podman socket does not exist at expected path (%(socket_path)s). "
                "Please check logs and ensure that Podman is correctly installed."
                % {"socket_path": socket_path}
            )
        )


def get_registry_from_image_name(
    image_name: str, default_registry: str | None = None
) -> str:
    """Get the registry, if set, from the given container image name."""
    if not default_registry:
        default_registry = settings.DEFAULT_PODMAN_REGISTRY
    if "/" not in image_name:
        return default_registry

    first_part = image_name.split("/", 1)[0]
    # Note that "localhost" is a known universal special case.
    return (
        first_part
        if "." in first_part or ":" in first_part or first_part == "localhost"
        else default_registry
    )


def ensure_cgroups_v2():
    """
    Ensure that cgroups v2 is enabled.

    Raises:
        PodmanIsNotReadyError: If cgroups v2 is not enabled.
    """
    logger.debug(_("Ensuring cgroups v2 is enabled."))
    stdout, __, exit_code = shell_utils.run_command(["podman", "info", "-f", "json"])
    logger.debug(stdout)

    if exit_code != 0:
        raise PodmanIsNotReadyError(_("Podman info command failed unexpectedly."))

    try:
        cgroups_version = json.loads(stdout).get("host", {}).get("cgroupVersion", None)
    except json.decoder.JSONDecodeError as e:
        logger.error(e)
        raise PodmanIsNotReadyError(
            _("Podman info failed to return valid JSON.")
        ) from e

    if cgroups_version != "v2":
        if not settings.runtime.quiet:
            print(
                ENABLE_CGROUPS_V2_LONG_MESSAGE
                % {"server_software_name": settings.SERVER_SOFTWARE_NAME}
            )
        raise PodmanIsNotReadyError(_("cgroups v2 is required but not available."))


def list_expected_podman_container_images():
    """List expected container images as defined by installed configs."""
    unique_images = set()

    unit_files = (
        settings.SYSTEMD_UNITS_DIR / unit_file
        for unit_file in settings.TEMPLATE_SYSTEMD_UNITS_FILENAMES
    )
    unit_files = (
        unit_file
        for unit_file in unit_files
        if unit_file.exists() and unit_file.suffix == ".container"
    )

    for unit_file in unit_files:
        unit_file_config = systemdunitparser.SystemdUnitParser()
        try:
            unit_file_config.read(unit_file)
        except configparser.MissingSectionHeaderError:
            logger.warning(
                _(
                    "Skipping the %(unit_file)s container file due to"
                    " missing section headers."
                ),
                {"unit_file": unit_file.name},
            )

        if "Container" in unit_file_config.sections() and (
            image := unit_file_config.get("Container", "Image")
        ):
            unique_images.add(image)

    return unique_images


def verify_podman_argument_string(name: str, value: object):
    """
    Verify the given value is a non-empty string.

    This function exists to sanity-check dynamic values that would be passed
    into podman subprocess calls such as image or secret names that we want
    to ensure are always strings and never empty.
    """
    if not isinstance(value, str):
        raise TypeError(
            _("Unexpected type '%(type)s' for %(name)s with value %(value)r.")
            % {"type": type(value).__name__, "name": name, "value": value},
        )
    if not value.strip():
        raise ValueError(_("Missing value for %(name)s.") % {"name": name})


def secret_exists(secret_name: str) -> bool:
    """Simply check if a secret exists."""
    verify_podman_argument_string(_("podman secret name"), secret_name)
    __, __, exit_code = shell_utils.run_command(
        ["podman", "secret", "exists", secret_name], raise_error=False
    )
    if exit_code == 0:
        logger.debug(
            _("Podman secret '%(secret_name)s' exists."), {"secret_name": secret_name}
        )
        return True
    else:
        logger.debug(
            _("Podman secret '%(secret_name)s' does not exist."),
            {"secret_name": secret_name},
        )
        return False


def set_secret(secret_name: str, secret_value: str, allow_replace=True) -> bool:
    """Set or replace a podman secret."""
    exists = secret_exists(secret_name)
    if exists:
        if allow_replace:
            logger.debug(
                _(
                    "Podman secret '%(secret_name)s' already exists "
                    "before setting a new value."
                ),
                {"secret_name": secret_name},
            )
        else:
            logger.error(
                _(
                    "Podman secret '%(secret_name)s' already exists "
                    "before setting a new value."
                ),
                {"secret_name": secret_name},
            )
            return False

    # TODO Simplify "delete + create" to just "create --replace" when we drop RHEL8.
    # While we support RHEL8, these commands must remain distinct because
    # RHEL8's podman CLI does not support the "--replace" argument.
    if exists:
        delete_secret(secret_name)
    __, __, exit_code = shell_utils.run_command(
        ["podman", "secret", "create", secret_name, "-"],
        raise_error=False,
        stdin=secret_value,
    )
    if exit_code == 0:
        logger.info(
            _("Podman secret '%(secret_name)s' was set."),
            {"secret_name": secret_name},
        )
        return True
    else:
        logger.error(
            _("Podman failed to set secret '%(secret_name)s'."),
            {"secret_name": secret_name},
        )
        return False


def delete_secret(secret_name: str) -> bool:
    """Delete a podman secret."""
    verify_podman_argument_string(_("podman secret name"), secret_name)
    __, __, exit_code = shell_utils.run_command(
        ["podman", "secret", "rm", secret_name], raise_error=False
    )
    if exit_code == 0:
        logger.info(
            _("Podman secret '%(secret_name)s' was removed."),
            {"secret_name": secret_name},
        )
        return True
    logger.error(
        _("Podman failed to remove secret '%(secret_name)s'."),
        {"secret_name": secret_name},
    )
    return False


def remove_image(image_id: str) -> bool:
    """Remove a container image ID."""
    verify_podman_argument_string(_("container image ID"), image_id)
    __, __, exit_code = shell_utils.run_command(
        ["podman", "image", "rm", image_id], raise_error=False
    )
    if exit_code == 0:
        logger.info(
            _("Removed container image '%(image_id)s'."), {"image_id": image_id}
        )
        return True
    logger.error(
        _("Failed to remove container image '%(image_id)s'."), {"image_id": image_id}
    )
    return False


def pull_image(image_id: str, wait_timeout: int = None) -> bool:
    """Pull the podman given container image name+tag."""
    verify_podman_argument_string(_("container image ID"), image_id)
    if wait_timeout is None:
        wait_timeout = settings.DEFAULT_PODMAN_PULL_TIMEOUT
    __, __, exit_code = shell_utils.run_command(
        ["podman", "pull", image_id], raise_error=False, wait_timeout=wait_timeout
    )
    if exit_code == 0:
        return True
    logger.error(_("Failed to pull image %(image)s."), {"image": image_id})
    return False


def get_secret_value(secret_name: str) -> str | None:
    """
    Get the value of an existing podman secret.

    Returns the secret value if it exists, otherwise None.
    """
    if not secret_exists(secret_name):
        return None
    stdout, __, exit_code = shell_utils.run_command(
        [
            "podman",
            "secret",
            "inspect",
            "--showsecret",
            "--format",
            "{{.SecretData}}",
            secret_name,
        ],
        raise_error=False,
        redact_output=True,
    )
    if exit_code == 0:
        return stdout
    logger.debug(
        _("Failed to retrieve podman secret '%(secret_name)s'."),
        {"secret_name": secret_name},
    )
    return None


def image_exists(image_name: str) -> bool:
    """Check if a container image exists locally."""
    verify_podman_argument_string(_("podman image name"), image_name)
    __, __, exit_code = shell_utils.run_command(
        ["podman", "image", "exists", image_name], raise_error=False
    )
    if exit_code == 0:
        logger.debug(
            _("Container image '%(image_name)s' exists locally."),
            {"image_name": image_name},
        )
        return True
    logger.debug(
        _("Container image '%(image_name)s' does not exist locally."),
        {"image_name": image_name},
    )
    return False


def get_missing_images() -> set[str]:
    """
    Get the set of required container images that are not present locally.

    Reads required images from installed config files and checks each one.
    Returns only the images that are missing.
    """
    expected_images = list_expected_podman_container_images()
    missing_images = set()

    for image in expected_images:
        if not image_exists(image):
            missing_images.add(image)

    if missing_images:
        logger.debug(
            _("Missing %(count)d of %(total)d required images."),
            {"count": len(missing_images), "total": len(expected_images)},
        )
    else:
        logger.debug(_("All required images are present locally."))

    return missing_images


def check_registry_login(registry: str) -> bool:
    """
    Check if the user has valid credentials for a registry.

    Runs 'podman login <registry>' with empty stdin to validate credentials
    against the remote registry without prompting for input.
    """
    verify_podman_argument_string(_("registry"), registry)
    # Pass empty stdin to prevent interactive prompt if credentials are invalid
    # Suppress stderr to avoid showing podman's EOF error to the user
    __, __, exit_code = shell_utils.run_command(
        ["podman", "login", registry],
        raise_error=False,
        stdin="",
        stderr=subprocess.DEVNULL,
    )
    if exit_code == 0:
        logger.debug(
            _("Valid credentials already exist for registry '%(registry)s'."),
            {"registry": registry},
        )
        return True
    logger.debug(
        _("Not logged in to registry '%(registry)s'."),
        {"registry": registry},
    )
    return False


def login_to_registry(registry: str) -> bool:
    """
    Prompt user for credentials and attempt to log in to the registry.

    Uses --password-stdin to avoid exposing password in process list.
    Returns True if login succeeds, False otherwise.
    """
    verify_podman_argument_string(_("registry"), registry)

    if settings.runtime.quiet:
        # podman login is required, but we can't prompt for credentials in quiet mode
        return False

    if not shell_utils.confirm(
        _("Log in to registry '%(registry)s'?") % {"registry": registry}
    ):
        return False

    print(_("Logging in to '%(registry)s'...") % {"registry": registry})

    username = input(_("Username: "))
    if not username.strip():
        logger.error(_("Username cannot be empty."))
        return False
    password = getpass.getpass(_("Password: "))
    if not password:
        logger.error(_("Password cannot be empty."))
        return False

    __, stderr, exit_code = shell_utils.run_command(
        ["podman", "login", registry, "--username", username, "--password-stdin"],
        raise_error=False,
        stdin=password,
        redact_output=False,  # TODO password should be safe via stdin, right ?
    )

    if exit_code == 0:
        logger.info(
            _("Successfully logged in to registry '%(registry)s'."),
            {"registry": registry},
        )
        return True

    logger.error(
        _("Failed to log in to registry '%(registry)s'."),
        {"registry": registry},
    )
    return False


def _log_missing_images_list(missing_images: set[str]) -> None:
    """Log the list of missing images."""
    for image in sorted(missing_images):
        logger.warning(
            _("Required container image '%(image)s' is missing."), {"image": image}
        )


def _ensure_registry_logins(missing_images: set[str]):
    """Ensure user is logged in to registries."""
    registries = {get_registry_from_image_name(img) for img in missing_images}

    for registry in registries:
        if not check_registry_login(registry):
            logger.info(
                _("Valid credentials do not exist for registry '%(registry)s'."),
                {"registry": registry},
            )
            if not login_to_registry(registry):
                logger.debug(
                    _("Could not log in to registry '%(registry)s'."),
                    {"registry": registry},
                )


def _pull_missing_images(missing_images: set[str]) -> bool:
    """
    Pull all missing images.

    Returns True if all pulls succeed, False otherwise.
    """
    if not settings.runtime.quiet:
        print(_("Pulling container images. This may take a few minutes."))

    for image in sorted(missing_images):
        logger.info(_("Pulling image: %(image)s"), {"image": image})
        if not pull_image(image):
            return False
    return True


def ensure_images() -> bool:
    """
    Ensure all required container images are present locally.

    Checks for missing images, prompts user to download if needed,
    handles registry login, and pulls images.

    Returns True if all images are present (or successfully pulled),
    False otherwise.
    """
    if not (missing_images := get_missing_images()):
        logger.info(_("All required container images are present."))
        return True

    _log_missing_images_list(missing_images)

    if not shell_utils.confirm(
        _("Should %(program)s pull missing images from the container registry?")
        % {"program": settings.PROGRAM_NAME}
    ):
        logger.error(
            _("Installation cannot proceed without all required container images.")
        )
        logger.info(_("For disconnected installation, see the online documentation."))
        return False

    _ensure_registry_logins(missing_images)

    if not _pull_missing_images(missing_images):
        return False

    logger.info(_("All required images have been pulled successfully."))

    return True
