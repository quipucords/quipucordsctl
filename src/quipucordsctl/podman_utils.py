"""Functions to simplify interfacing with podman."""

import configparser
import json
import logging
import os
import pathlib
import sys
import textwrap
from gettext import gettext as _
from urllib import parse

from quipucordsctl import settings, shell_utils, systemdunitparser

logger = logging.getLogger(__name__)
MACOS_DEFAULT_PODMAN_URL = "unix:///var/run/docker.sock"
DEFAULT_PODMAN_PULL_TIMEOUT = 600  # seconds, or 10 minutes
ENABLE_CGROUPS_V2_LONG_MESSAGE = _(
    textwrap.dedent(
        """
        This system is not configured to use cgroups v2 which is required for %(server_software_name)s.
        To enable cgroups v2 (a.k.a. cgroup2fs), you may need to update your kernel arguments and reboot.
        Please run the following commands before using %(server_software_name)s:

            sudo grubby --update-kernel=ALL --args="systemd.unified_cgroup_hierarchy=1"
            sudo reboot
        """  # noqa: E501
    )
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
    image_name: str, default_registry: str = "registry.redhat.io"
) -> str:
    """Get the registry, if set, from the given container image name."""
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


def secret_exists(secret_name: str) -> bool:
    """Simply check if a secret exists."""
    __, __, exit_code = shell_utils.run_command(
        ["podman", "secret", "exists", str(secret_name)], raise_error=False
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
        ["podman", "secret", "create", str(secret_name), "-"],
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
    __, __, exit_code = shell_utils.run_command(
        ["podman", "secret", "rm", str(secret_name)], raise_error=False
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
    """Remove a podman image ID."""
    __, __, exit_code = shell_utils.run_command(
        ["podman", "image", "rm", str(image_id)], raise_error=False
    )
    if exit_code == 0:
        logger.info(
            _("Podman image '%(image_id)s' was removed."), {"image_id": image_id}
        )
        return True
    logger.error(
        _("Podman failed to remove image '%(image_id)s'."), {"image_id": image_id}
    )
    return False


def pull_image(nametag: str, wait_timeout: int = None) -> bool:
    """Pull the podman given container image name+tag."""
    if wait_timeout is None:
        wait_timeout = DEFAULT_PODMAN_PULL_TIMEOUT
    __, __, exit_code = shell_utils.run_command(
        ["podman", "pull", str(nametag)], raise_error=False, wait_timeout=wait_timeout
    )
    if exit_code == 0:
        return True
    logger.error(_("Failed to pull image %(image)s."), {"image": nametag})
    return False
